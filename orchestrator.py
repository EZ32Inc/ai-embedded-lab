import argparse
import json
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from notifiers import discord_webhook
from ael import run_manager
from ael.adapter_registry import AdapterRegistry
from ael.runner import run_plan

_INSTRUMENT_SELFTEST_CACHE = {}


def _simple_yaml_load(path):
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        data = {}
        stack = [data]
        indent_stack = [0]
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip(" "))
                key, _, value = line.strip().partition(":")
                value = value.strip().strip('"')
                while indent < indent_stack[-1]:
                    stack.pop()
                    indent_stack.pop()
                if value == "":
                    obj = {}
                    stack[-1][key] = obj
                    stack.append(obj)
                    indent_stack.append(indent)
                else:
                    stack[-1][key] = value
        return data


def _deep_merge(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _parse_wiring(s):
    wiring = {}
    if not s:
        return wiring
    parts = [p.strip() for p in s.split() if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        wiring[k.strip()] = v.strip()
    return wiring


def _normalize_probe_cfg(raw):
    probe = raw.get("probe", {}) if isinstance(raw, dict) else {}
    connection = raw.get("connection", {}) if isinstance(raw, dict) else {}
    cfg = dict(probe)

    if "ip" not in cfg and "ip" in connection:
        cfg["ip"] = connection["ip"]
    if "gdb_port" not in cfg and "gdb_port" in connection:
        cfg["gdb_port"] = connection["gdb_port"]

    if "gdb_cmd" not in cfg:
        cfg["gdb_cmd"] = raw.get("gdb_cmd") if isinstance(raw, dict) else None

    return cfg


def _merge_wiring(defaults, overrides):
    merged = dict(defaults or {})
    merged.update(overrides or {})
    return merged


def _require_wiring(merged, required):
    missing = [k for k in required if k not in merged or not merged[k]]
    if missing:
        for k in missing:
            merged[k] = "UNKNOWN"
        print(f"I am guessing {', '.join(missing)} — please confirm.")
    return merged


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info():
    info = {"commit": "", "dirty": False, "status": ""}
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            info["commit"] = (res.stdout or "").strip()

        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            status = (res.stdout or "").strip()
            info["status"] = status
            info["dirty"] = bool(status)
    except Exception:
        pass
    return info


def _write_json(path, data):
    try:
        run_manager.ensure_parent(Path(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except Exception:
        pass


def _resolve_builder_kind(board_cfg):
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg, dict) else {}
    if isinstance(build_cfg, dict):
        kind = str(build_cfg.get("type", "")).strip().lower()
        if kind:
            return kind
    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg, dict) else {}
    if isinstance(flash_cfg, dict):
        if flash_cfg.get("method") == "idf_esptool":
            return "idf"
        if flash_cfg.get("gdb_launch_cmds"):
            return "arm_debug"
    return "cmake"


def _default_firmware_path(board_cfg):
    root = os.path.dirname(__file__)
    if _resolve_builder_kind(board_cfg) == "arm_debug":
        return os.path.join(root, "artifacts", "build_stm32", "stm32f103_app.elf")
    return os.path.join(root, "artifacts", "build", "pico_blink.elf")


def _copy_artifacts(firmware_path, artifacts_dir):
    if not firmware_path:
        return []
    copied = []
    base = Path(firmware_path)
    candidates = [base]
    candidates.append(base.with_suffix(".uf2"))
    candidates.append(base.with_suffix(".bin"))
    for p in candidates:
        if p.exists():
            dest = Path(artifacts_dir) / p.name
            try:
                dest.write_bytes(p.read_bytes())
                copied.append(str(dest))
            except Exception:
                pass
    return copied


@contextmanager
def _tee_output(log_path, output_mode):
    tee, f = run_manager.open_tee(Path(log_path), output_mode, console=sys.stdout)
    orig_out = sys.stdout
    orig_err = sys.stderr
    sys.stdout = tee
    sys.stderr = tee
    try:
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        sys.stdout = orig_out
        sys.stderr = orig_err
        f.close()


def _triage(stage, pre_info):
    print("FAIL: stage=" + stage)
    if stage == "preflight":
        if not pre_info.get("ping_ok"):
            print("Hint: probe not reachable. Check power and Wi-Fi/AP connection.")
        if not pre_info.get("tcp_ok"):
            print("Hint: debug port closed. Check debug server endpoint and IP/port.")
        if not pre_info.get("monitor_ok"):
            print("Hint: debug server connected but monitor failed. Try power-cycle target and probe.")
        if not pre_info.get("la_ok"):
            print("Hint: LA web API failed. Check web credentials and HTTPS settings.")
        return
    if stage == "build":
        print("Hint: check SDK path, build toolchain, and build dependencies.")
        return
    if stage == "flash":
        print("Hint: verify SWD wiring, target power, and only one debug session connected.")
        print("Hint: try a reset or power-cycle, then rerun.")
        return
    if stage == "verify":
        print("Hint: verify GPIO mapping and wiring for verify pin.")
        print("Hint: if edges are too few, lower LA sample rate or increase blink frequency.")
        return
    if stage == "observe_uart":
        print("Hint: check UART port selection and that no other process holds the port.")
        print("Hint: ensure target is running and baud rate matches firmware.")
        return


def _emit_event(event, notify_cfg):
    if not isinstance(notify_cfg, dict):
        return
    try:
        discord_webhook.notify(event, notify_cfg)
    except Exception as exc:
        print(f"Notify: error {exc}")


def _parse_endpoint_hint(endpoint_hint):
    if not endpoint_hint or ":" not in str(endpoint_hint):
        return {}
    host, port = str(endpoint_hint).rsplit(":", 1)
    try:
        return {"host": host.strip(), "port": int(port.strip())}
    except Exception:
        return {}


def _resolve_instrument_context(test_raw, board_cfg):
    explicit = {}
    if isinstance(test_raw, dict):
        explicit = test_raw.get("instrument", {}) if isinstance(test_raw.get("instrument"), dict) else {}
    if not explicit and isinstance(board_cfg, dict):
        explicit = board_cfg.get("instrument", {}) if isinstance(board_cfg.get("instrument"), dict) else {}
    instrument_id = explicit.get("id")
    if not instrument_id:
        return None, {}, {}

    manifest = {}
    try:
        from ael.instruments.registry import InstrumentRegistry

        manifest = InstrumentRegistry().get(instrument_id) or {}
    except Exception:
        manifest = {}

    tcp_cfg = explicit.get("tcp", {}) if isinstance(explicit.get("tcp"), dict) else {}
    if "host" not in tcp_cfg or "port" not in tcp_cfg:
        endpoint = {}
        transports = manifest.get("transports", []) if isinstance(manifest, dict) else []
        for t in transports:
            if isinstance(t, dict) and t.get("type") == "tcp":
                endpoint = _parse_endpoint_hint(t.get("endpoint_hint"))
                if endpoint:
                    break
        wifi_cfg = manifest.get("wifi", {}) if isinstance(manifest.get("wifi"), dict) else {}
        host = tcp_cfg.get("host") or endpoint.get("host") or wifi_cfg.get("ap_ip")
        port = tcp_cfg.get("port") or endpoint.get("port") or wifi_cfg.get("tcp_port")
        tcp_cfg = {"host": host, "port": port}

    return instrument_id, tcp_cfg, manifest


def _is_meter_digital_verify_test(test_raw):
    if not isinstance(test_raw, dict):
        return False
    inst = test_raw.get("instrument", {})
    if not isinstance(inst, dict) or inst.get("id") != "esp32s3_dev_c_meter":
        return False
    conns = test_raw.get("connections", {})
    if not isinstance(conns, dict):
        return False
    links = conns.get("dut_to_instrument", [])
    return isinstance(links, list) and len(links) > 0


def _run_meter_digital_verify(test_raw, board_cfg, run_paths):
    instrument_id, tcp_cfg, _manifest = _resolve_instrument_context(test_raw, board_cfg)
    if instrument_id != "esp32s3_dev_c_meter":
        return False, [], "meter instrument not configured"

    links = test_raw.get("connections", {}).get("dut_to_instrument", [])
    pins = []
    expected_by_gpio = {}
    for item in links:
        if not isinstance(item, dict):
            continue
        if item.get("inst_gpio") is None:
            continue
        inst_gpio = int(item.get("inst_gpio"))
        expect = str(item.get("expect", "")).strip().lower()
        pins.append(inst_gpio)
        expected_by_gpio[inst_gpio] = {
            "expect": expect,
            "dut_gpio": item.get("dut_gpio"),
            "freq_hz": item.get("freq_hz"),
        }
    if not pins:
        return False, [], "no instrument pins configured"

    duration_ms = 500
    meas_cfg = test_raw.get("measurement", {})
    if isinstance(meas_cfg, dict) and meas_cfg.get("duration_ms") is not None:
        duration_ms = int(meas_cfg.get("duration_ms"))
    else:
        instrument_cfg = test_raw.get("instrument", {})
        if isinstance(instrument_cfg, dict):
            meter_cfg = instrument_cfg.get("measure", {})
            if isinstance(meter_cfg, dict) and meter_cfg.get("duration_ms") is not None:
                duration_ms = int(meter_cfg.get("duration_ms"))

    cfg = {
        "host": tcp_cfg.get("host"),
        "port": int(tcp_cfg.get("port")) if tcp_cfg.get("port") is not None else 9000,
    }
    instrument_path = str(Path(run_paths.artifacts_dir) / "instrument_digital.json")
    verify_path = str(Path(run_paths.artifacts_dir) / "verify_result.json")
    analog_path = str(Path(run_paths.artifacts_dir) / "instrument_voltage.json")

    meas = esp32s3_dev_c_meter_tcp.measure_digital(
        cfg,
        pins=pins,
        duration_ms=duration_ms,
        out_path=instrument_path,
    )
    pin_rows = meas.get("pins", []) if isinstance(meas, dict) else []
    actual_by_gpio = {}
    for row in pin_rows:
        if isinstance(row, dict) and row.get("gpio") is not None:
            actual_by_gpio[int(row.get("gpio"))] = row

    mismatches = []
    checks = []
    for gpio, exp in expected_by_gpio.items():
        row = actual_by_gpio.get(gpio)
        if not row:
            mismatches.append({"inst_gpio": gpio, "reason": "missing_measurement"})
            continue
        actual_state = str(row.get("state", "")).strip().lower()
        expect_state = exp.get("expect", "")
        check = {
            "inst_gpio": gpio,
            "dut_gpio": exp.get("dut_gpio"),
            "expect": expect_state,
            "actual": actual_state,
            "samples": row.get("samples"),
            "ones": row.get("ones"),
            "zeros": row.get("zeros"),
            "transitions": row.get("transitions"),
        }
        checks.append(check)
        if actual_state != expect_state:
            mismatches.append(
                {
                    "inst_gpio": gpio,
                    "reason": "state_mismatch",
                    "expect": expect_state,
                    "actual": actual_state,
                }
            )
            continue
        if expect_state == "toggle":
            transitions = int(row.get("transitions", 0))
            if transitions <= 0:
                mismatches.append(
                    {
                        "inst_gpio": gpio,
                        "reason": "toggle_no_transitions",
                        "transitions": transitions,
                    }
                )

    analog_checks = []
    analog_links = test_raw.get("connections", {}).get("dut_to_instrument_analog", [])
    analog_measurements = []

    def _extract_voltage_v(payload):
        if not isinstance(payload, dict):
            return None
        direct_v_keys = ("voltage_v", "v", "value_v", "voltage", "value")
        for key in direct_v_keys:
            val = payload.get(key)
            if isinstance(val, (int, float)):
                f = float(val)
                if f > 10.0:
                    return f / 1000.0
                return f
        mv = payload.get("mv")
        if isinstance(mv, (int, float)):
            return float(mv) / 1000.0
        result = payload.get("result")
        if isinstance(result, dict):
            return _extract_voltage_v(result)
        return None

    for item in analog_links if isinstance(analog_links, list) else []:
        if not isinstance(item, dict):
            continue
        adc_gpio = item.get("inst_adc_gpio")
        if adc_gpio is None:
            continue
        adc_gpio = int(adc_gpio)
        avg = int(item.get("avg", 16))
        min_v = item.get("expect_v_min")
        max_v = item.get("expect_v_max")
        if min_v is not None:
            min_v = float(min_v)
        if max_v is not None:
            max_v = float(max_v)
        if min_v is None and max_v is None and item.get("expect_v") is not None:
            center = float(item.get("expect_v"))
            tol = float(item.get("tolerance_v", 0.2))
            min_v = center - tol
            max_v = center + tol

        meas_v = esp32s3_dev_c_meter_tcp.measure_voltage(cfg, gpio=adc_gpio, avg=avg, out_path=None)
        analog_measurements.append(
            {
                "inst_adc_gpio": adc_gpio,
                "avg": avg,
                "response": meas_v,
            }
        )
        measured_v = _extract_voltage_v(meas_v)
        check = {
            "inst_adc_gpio": adc_gpio,
            "dut_signal": item.get("dut_signal"),
            "expect_v_min": min_v,
            "expect_v_max": max_v,
            "measured_v": measured_v,
            "avg": avg,
        }
        analog_checks.append(check)

        if measured_v is None:
            mismatches.append({"inst_adc_gpio": adc_gpio, "reason": "voltage_missing"})
            continue
        if min_v is not None and measured_v < min_v:
            mismatches.append(
                {
                    "inst_adc_gpio": adc_gpio,
                    "reason": "voltage_below_min",
                    "expect_v_min": min_v,
                    "measured_v": measured_v,
                }
            )
        if max_v is not None and measured_v > max_v:
            mismatches.append(
                {
                    "inst_adc_gpio": adc_gpio,
                    "reason": "voltage_above_max",
                    "expect_v_max": max_v,
                    "measured_v": measured_v,
                }
            )

    if analog_measurements:
        _write_json(analog_path, {"ok": True, "measurements": analog_measurements})

    ok = len(mismatches) == 0
    verify_payload = {
        "ok": ok,
        "type": "instrument_digital_verify",
        "duration_ms": duration_ms,
        "instrument_id": "esp32s3_dev_c_meter",
        "host": cfg.get("host"),
        "port": cfg.get("port"),
        "checks": checks,
        "analog_checks": analog_checks,
        "mismatches": mismatches,
    }
    _write_json(verify_path, verify_payload)
    err = "" if ok else "instrument digital verification failed"
    artifacts = [instrument_path, verify_path]
    if analog_measurements:
        artifacts.append(analog_path)
    return ok, artifacts, err


def _resolve_board_path(repo_root, board_arg):
    if not board_arg:
        return None, None
    p = Path(board_arg)
    if p.exists() and p.is_file():
        return str(p), p.stem
    board_id = board_arg
    board_path = Path(repo_root) / "configs" / "boards" / f"{board_id}.yaml"
    return str(board_path), board_id


def _run_instrument_selftest(test_raw, board_cfg, run_paths):
    instrument_id, tcp_cfg, manifest = _resolve_instrument_context(test_raw, board_cfg)
    if not instrument_id:
        return True, None, None

    selftest_manifest = manifest.get("selftest", {}) if isinstance(manifest, dict) else {}
    if instrument_id != "esp32s3_dev_c_meter" and not selftest_manifest:
        return True, None, None

    cache_key = (run_paths.run_id, instrument_id)
    if cache_key in _INSTRUMENT_SELFTEST_CACHE:
        cached = _INSTRUMENT_SELFTEST_CACHE[cache_key]
        return bool(cached.get("pass")), cached.get("artifact"), cached.get("error")

    artifact_path = str(Path(run_paths.artifacts_dir) / "instrument_selftest.json")
    cfg = {
        "host": tcp_cfg.get("host"),
        "port": int(tcp_cfg.get("port")) if tcp_cfg.get("port") is not None else 9000,
        "artifacts_dir": str(run_paths.artifacts_dir),
    }

    dig = selftest_manifest.get("digital", {}) if isinstance(selftest_manifest.get("digital"), dict) else {}
    adc = selftest_manifest.get("adc", {}) if isinstance(selftest_manifest.get("adc"), dict) else {}
    test_self = test_raw.get("selftest", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("selftest"), dict) else {}
    test_dig = test_self.get("digital", {}) if isinstance(test_self.get("digital"), dict) else {}
    test_adc = test_self.get("adc", {}) if isinstance(test_self.get("adc"), dict) else {}

    out_gpio = int(test_dig.get("out_gpio", dig.get("out_gpio", 15)))
    in_gpio = int(test_dig.get("in_gpio", dig.get("in_gpio", 11)))
    dur_ms = int(test_dig.get("dur_ms", dig.get("dur_ms", 200)))
    freq_hz = int(test_dig.get("freq_hz", dig.get("freq_hz", 1000)))
    adc_out = int(test_adc.get("out_gpio", adc.get("out_gpio", 16)))
    adc_in = int(test_adc.get("adc_gpio", adc.get("adc_gpio", 4)))
    avg = int(test_adc.get("avg", adc.get("avg", 16)))
    settle_ms = int(test_adc.get("settle_ms", adc.get("settle_ms", 20)))

    try:
        payload = esp32s3_dev_c_meter_tcp.selftest(
            cfg,
            out_gpio=out_gpio,
            in_gpio=in_gpio,
            adc_out=adc_out,
            adc_in=adc_in,
            dur_ms=dur_ms,
            freq_hz=freq_hz,
            avg=avg,
            settle_ms=settle_ms,
            out_path=artifact_path,
        )
        cache_value = {"pass": bool(payload.get("pass")), "artifact": artifact_path, "error": payload.get("error", "")}
        _INSTRUMENT_SELFTEST_CACHE[cache_key] = cache_value
        return bool(payload.get("pass")), artifact_path, payload.get("error", "")
    except Exception as exc:
        err_payload = {
            "ok": False,
            "type": "selftest",
            "pass": False,
            "error": str(exc),
            "instrument_id": instrument_id,
            "host": cfg.get("host"),
            "port": cfg.get("port"),
        }
        _write_json(artifact_path, err_payload)
        cache_value = {"pass": False, "artifact": artifact_path, "error": str(exc)}
        _INSTRUMENT_SELFTEST_CACHE[cache_key] = cache_value
        return False, artifact_path, str(exc)


def _instrument_selftest_requested(test_raw, board_cfg):
    if isinstance(test_raw, dict):
        if bool(test_raw.get("instrument_selftest")):
            return True
        selftest_cfg = test_raw.get("selftest", {})
        if isinstance(selftest_cfg, dict) and bool(selftest_cfg.get("enabled")):
            return True
        instrument_cfg = test_raw.get("instrument", {})
        if isinstance(instrument_cfg, dict) and bool(instrument_cfg.get("selftest")):
            return True
        if isinstance(instrument_cfg, dict) and bool(instrument_cfg.get("run_selftest")):
            return True
    if isinstance(board_cfg, dict) and bool(board_cfg.get("instrument_selftest")):
        return True
    return False


def run_pipeline(
    probe_path,
    board_arg,
    test_path,
    wiring,
    output_mode="normal",
    skip_flash=False,
    no_build=False,
    verify_only=False,
    return_paths=False,
):
    repo_root = os.path.dirname(__file__)
    if not test_path:
        test_path = os.path.join(repo_root, "tests", "blink_gpio.json")

    try:
        with open(test_path, "r", encoding="utf-8") as f:
            test_raw = json.load(f)
    except Exception:
        test_raw = {}

    board_path, board_id = _resolve_board_path(repo_root, board_arg)
    if not board_id:
        board_id = test_raw.get("board", "unknown") if isinstance(test_raw, dict) else "unknown"
        if board_id and board_id != "unknown":
            board_path, _ = _resolve_board_path(repo_root, board_id)

    run_paths = run_manager.create_run(board_id or "unknown", test_path, repo_root)
    for p in [
        run_paths.build_log,
        run_paths.flash_log,
        run_paths.observe_log,
        run_paths.observe_uart_step_log,
        run_paths.verify_log,
        run_paths.preflight_log,
    ]:
        Path(p).write_text("")
    Path(run_paths.observe_uart_log).write_bytes(b"")
    _write_json(run_paths.measure, {"ok": False, "metrics": {}, "reasons": ["not_run"]})
    _write_json(run_paths.result, {"ok": False, "failed_step": "", "error_summary": ""})
    _write_json(run_paths.flash_json, {"ok": False, "attempts": [], "strategy_used": "", "speed_khz": None})
    _write_json(run_paths.uart_observe, {"ok": False, "bytes": 0, "lines": 0})

    probe_raw = _simple_yaml_load(probe_path) if probe_path else {}
    board_raw = _simple_yaml_load(board_path) if board_path else {}
    effective = _deep_merge(_deep_merge(probe_raw, board_raw), test_raw)
    _write_json(run_paths.config_effective, effective)
    notify_cfg = effective.get("notify", {}) if isinstance(effective, dict) else {}

    run_started = datetime.now()
    run_started_mono = time.monotonic()
    git_info = _git_info()
    meta = {
        "run_id": run_paths.run_id,
        "started_at": run_started.isoformat(),
        "probe_path": probe_path,
        "board_path": board_path,
        "test_path": test_path,
        "git_commit": git_info.get("commit"),
        "git_dirty": git_info.get("dirty"),
        "git_status": git_info.get("status"),
    }

    probe_cfg = _normalize_probe_cfg(probe_raw)
    board_cfg = board_raw.get("board", {}) if isinstance(board_raw, dict) else {}
    if not isinstance(board_cfg, dict):
        board_cfg = {}
    else:
        board_cfg = dict(board_cfg)

    test_build = test_raw.get("build", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("build"), dict) else {}
    firmware_override = test_raw.get("firmware") if isinstance(test_raw, dict) else None
    project_override = test_build.get("project_dir") or firmware_override
    if project_override:
        build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
        build_cfg = dict(build_cfg)
        build_cfg["type"] = "idf"
        build_cfg["project_dir"] = str(project_override)
        board_cfg["build"] = build_cfg

    wiring_overrides = _parse_wiring(wiring or "")
    wiring_cfg = _merge_wiring(board_cfg.get("default_wiring", {}), wiring_overrides)
    wiring_cfg = _require_wiring(wiring_cfg, ["swd", "reset", "verify"])

    test_name = test_raw.get("name") if isinstance(test_raw, dict) else None
    instrument_cfg = test_raw.get("instrument", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("instrument"), dict) else {}
    instrument_id = instrument_cfg.get("id")
    instrument_host = instrument_cfg.get("tcp", {}).get("host") if isinstance(instrument_cfg.get("tcp"), dict) else None
    instrument_port = instrument_cfg.get("tcp", {}).get("port") if isinstance(instrument_cfg.get("tcp"), dict) else None

    print("AI: starting pipeline")
    if instrument_id:
        banner_name = test_name or instrument_id
        banner_host = instrument_host or "unknown"
        banner_port = instrument_port if instrument_port is not None else "unknown"
        print(f"Using instrument: {banner_name} ({instrument_id}) @ {banner_host}:{banner_port}")
    else:
        print(f"Using probe: {probe_cfg.get('name', 'unknown')} @ {probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}")
    print(f"Using board: {board_cfg.get('name', 'unknown')} target={board_cfg.get('target', 'unknown')}")
    print(f"Wiring: swd={wiring_cfg.get('swd')} reset={wiring_cfg.get('reset')} verify={wiring_cfg.get('verify')}")

    _emit_event(
        {
            "type": "run_started",
            "severity": "info",
            "run_id": run_paths.run_id,
            "dut": board_id or board_cfg.get("name", "unknown"),
            "bench": None,
            "summary": "run started",
            "artifacts_path": str(run_paths.root),
            "timestamp": run_started.isoformat(),
            "log_paths": {
                "build": str(run_paths.build_log),
                "flash": str(run_paths.flash_log),
                "observe": str(run_paths.observe_log),
                "verify": str(run_paths.verify_log),
                "uart": str(run_paths.observe_uart_log),
            },
        },
        notify_cfg,
    )

    def _failed_step_name(runner_result):
        if runner_result.get("ok"):
            return ""
        steps = runner_result.get("steps", []) if isinstance(runner_result, dict) else []
        for entry in reversed(steps):
            if isinstance(entry, dict) and not entry.get("ok", False):
                return str(entry.get("name", ""))
        return ""

    def _code_from_failed_step(name):
        if not name:
            return 1
        if name.startswith("preflight"):
            return 2
        if name.startswith("instrument_selftest"):
            return 7
        if name.startswith("build"):
            return 3
        if name.startswith("load"):
            return 4
        if name.startswith("check_uart"):
            return 5
        if name.startswith("check"):
            return 6
        return 1

    def _extract_firmware_from_runner(runner_result):
        steps = runner_result.get("steps", []) if isinstance(runner_result, dict) else []
        for entry in reversed(steps):
            if not isinstance(entry, dict):
                continue
            payload = entry.get("result", {})
            if isinstance(payload, dict) and payload.get("firmware_path"):
                return str(payload.get("firmware_path"))
        return None

    plan_steps = []
    preflight_cfg = test_raw.get("preflight", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("preflight"), dict) else {}
    preflight_enabled = True if preflight_cfg.get("enabled") is None else bool(preflight_cfg.get("enabled"))
    if preflight_enabled:
        plan_steps.append(
            {
                "name": "preflight",
                "type": "preflight.probe",
                "inputs": {
                    "probe_cfg": probe_cfg,
                    "out_json": str(run_paths.preflight),
                    "output_mode": output_mode,
                    "log_path": str(run_paths.preflight_log),
                },
            }
        )
    else:
        _write_json(run_paths.preflight, {"skipped": True})
        with _tee_output(run_paths.preflight_log, output_mode):
            print("Preflight: SKIPPED (test config)")

    if _instrument_selftest_requested(test_raw, board_cfg):
        instrument_id, tcp_cfg, manifest = _resolve_instrument_context(test_raw, board_cfg)
        selftest_manifest = manifest.get("selftest", {}) if isinstance(manifest, dict) else {}
        dig = selftest_manifest.get("digital", {}) if isinstance(selftest_manifest.get("digital"), dict) else {}
        adc = selftest_manifest.get("adc", {}) if isinstance(selftest_manifest.get("adc"), dict) else {}
        test_self = test_raw.get("selftest", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("selftest"), dict) else {}
        test_dig = test_self.get("digital", {}) if isinstance(test_self.get("digital"), dict) else {}
        test_adc = test_self.get("adc", {}) if isinstance(test_self.get("adc"), dict) else {}
        plan_steps.append(
            {
                "name": "instrument_selftest",
                "type": "check.instrument_selftest",
                "inputs": {
                    "cfg": {
                        "host": tcp_cfg.get("host"),
                        "port": int(tcp_cfg.get("port")) if tcp_cfg.get("port") is not None else 9000,
                        "artifacts_dir": str(run_paths.artifacts_dir),
                    },
                    "params": {
                        "out_gpio": int(test_dig.get("out_gpio", dig.get("out_gpio", 15))),
                        "in_gpio": int(test_dig.get("in_gpio", dig.get("in_gpio", 11))),
                        "dur_ms": int(test_dig.get("dur_ms", dig.get("dur_ms", 200))),
                        "freq_hz": int(test_dig.get("freq_hz", dig.get("freq_hz", 1000))),
                        "adc_out": int(test_adc.get("out_gpio", adc.get("out_gpio", 16))),
                        "adc_in": int(test_adc.get("adc_gpio", adc.get("adc_gpio", 4))),
                        "avg": int(test_adc.get("avg", adc.get("avg", 16))),
                        "settle_ms": int(test_adc.get("settle_ms", adc.get("settle_ms", 20))),
                    },
                    "out_path": str(Path(run_paths.artifacts_dir) / "instrument_selftest.json"),
                },
            }
        )

    build_kind = _resolve_builder_kind(board_cfg)
    known_firmware_path = None
    if not verify_only and not no_build:
        plan_steps.append(
            {
                "name": "build",
                "type": f"build.{build_kind}",
                "inputs": {
                    "board_cfg": board_cfg,
                    "output_mode": output_mode,
                    "log_path": str(run_paths.build_log),
                },
            }
        )
    elif not verify_only and no_build:
        known_firmware_path = _default_firmware_path(board_cfg)
        if not os.path.exists(known_firmware_path):
            result = {
                "ok": False,
                "failed_step": "build",
                "error_summary": "no build artifacts found",
                "logs": {
                    "preflight": str(run_paths.preflight_log),
                    "build": str(run_paths.build_log),
                    "flash": str(run_paths.flash_log),
                    "observe": str(run_paths.observe_log),
                    "observe_uart": str(run_paths.observe_uart_step_log),
                    "observe_uart_raw": str(run_paths.observe_uart_log),
                    "verify": str(run_paths.verify_log),
                },
                "artifacts": [],
                "json": {
                    "flash": str(run_paths.flash_json),
                    "measure": str(run_paths.measure),
                    "uart_observe": str(run_paths.uart_observe),
                    "preflight": str(run_paths.preflight),
                    "meta": str(run_paths.meta),
                    "config_effective": str(run_paths.config_effective),
                    "instrument_selftest": str(Path(run_paths.artifacts_dir) / "instrument_selftest.json"),
                    "instrument_digital": str(Path(run_paths.artifacts_dir) / "instrument_digital.json"),
                    "verify_result": str(Path(run_paths.artifacts_dir) / "verify_result.json"),
                },
            }
            _write_json(run_paths.result, result)
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return (3, run_paths) if return_paths else 3

    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg, dict) else {}
    reset_unwired = wiring_cfg.get("reset") in ("NC", "NONE", "NONE/NC", "N/C", "NA")
    if reset_unwired:
        flash_cfg = dict(flash_cfg)
        flash_cfg["reset_available"] = False
    if not verify_only and not skip_flash:
        method = str(flash_cfg.get("method", "gdbmi")).strip()
        if method == "idf_esptool":
            if board_cfg.get("build", {}):
                flash_cfg = dict(flash_cfg)
                flash_cfg["project_dir"] = board_cfg.get("build", {}).get("project_dir")
            target = board_cfg.get("target")
            if target:
                flash_cfg = dict(flash_cfg)
                flash_cfg["target"] = target
                flash_cfg["build_dir"] = os.path.join(repo_root, "artifacts", f"build_{target}")
        plan_steps.append(
            {
                "name": "load",
                "type": "load.idf_esptool" if method == "idf_esptool" else "load.gdbmi",
                "inputs": {
                    "probe_cfg": probe_cfg,
                    "firmware_path": known_firmware_path,
                    "flash_cfg": flash_cfg,
                    "flash_json_path": str(run_paths.flash_json),
                    "output_mode": output_mode,
                    "log_path": str(run_paths.flash_log),
                },
            }
        )
    elif skip_flash and not verify_only:
        with _tee_output(run_paths.flash_log, output_mode):
            print("Flash: SKIPPED (user requested skip)")
        _write_json(
            run_paths.flash_json,
            {"ok": False, "attempts": [], "strategy_used": "skipped", "speed_khz": flash_cfg.get("speed_khz")},
        )

    observe_uart_cfg = {}
    if isinstance(effective, dict):
        observe_uart_cfg = effective.get("observe_uart", {}) or {}
    if isinstance(observe_uart_cfg, dict) and observe_uart_cfg.get("enabled"):
        observe_uart_cfg = dict(observe_uart_cfg)
        observe_uart_cfg.setdefault("auto_reset_on_download", True)
        observe_uart_cfg.setdefault("reset_strategy", board_cfg.get("uart_reset_strategy", "none"))
        plan_steps.append(
            {
                "name": "check_uart",
                "type": "check.uart_log",
                "inputs": {
                    "observe_uart_cfg": observe_uart_cfg,
                    "raw_log_path": str(run_paths.observe_uart_log),
                    "out_json": str(run_paths.uart_observe),
                    "flash_json_path": str(run_paths.flash_json),
                    "output_mode": output_mode,
                    "log_path": str(run_paths.observe_uart_step_log),
                },
            }
        )

    if _is_meter_digital_verify_test(test_raw):
        instrument_id, tcp_cfg, _manifest = _resolve_instrument_context(test_raw, board_cfg)
        links = test_raw.get("connections", {}).get("dut_to_instrument", [])
        analog_links = test_raw.get("connections", {}).get("dut_to_instrument_analog", [])
        duration_ms = 500
        meas_cfg = test_raw.get("measurement", {})
        if isinstance(meas_cfg, dict) and meas_cfg.get("duration_ms") is not None:
            duration_ms = int(meas_cfg.get("duration_ms"))
        plan_steps.append(
            {
                "name": "check_meter",
                "type": "check.instrument_signature",
                "inputs": {
                    "instrument_id": instrument_id,
                    "cfg": {
                        "host": tcp_cfg.get("host"),
                        "port": int(tcp_cfg.get("port")) if tcp_cfg.get("port") is not None else 9000,
                    },
                    "links": links,
                    "analog_links": analog_links,
                    "duration_ms": duration_ms,
                    "digital_out": str(Path(run_paths.artifacts_dir) / "instrument_digital.json"),
                    "verify_out": str(Path(run_paths.artifacts_dir) / "verify_result.json"),
                    "analog_out": str(Path(run_paths.artifacts_dir) / "instrument_voltage.json"),
                },
            }
        )
    else:
        observe_map = board_cfg.get("observe_map", {}) if isinstance(board_cfg, dict) else {}
        test_pin = test_raw.get("pin") if isinstance(test_raw, dict) else None
        pin_value = test_pin
        if test_pin and isinstance(observe_map, dict) and test_pin in observe_map:
            pin_value = observe_map.get(test_pin)
        if not pin_value:
            pin_value = wiring_cfg.get("verify")
        check_probe_cfg = dict(probe_cfg)
        if isinstance(test_raw, dict) and test_raw.get("sample_rate_hz"):
            check_probe_cfg["la_sample_rate"] = int(test_raw.get("sample_rate_hz"))
        duration_s = float(test_raw.get("duration_s", 3.0)) if isinstance(test_raw, dict) else 3.0
        if isinstance(test_raw, dict) and test_raw.get("duration_ms") and not test_raw.get("duration_s"):
            duration_s = float(test_raw.get("duration_ms")) / 1000.0
        plan_steps.append(
            {
                "name": "check_signal",
                "type": "check.signal_verify",
                "inputs": {
                    "probe_cfg": check_probe_cfg,
                    "pin": pin_value,
                    "duration_s": duration_s,
                    "expected_hz": float(test_raw.get("expected_hz", 1.0)) if isinstance(test_raw, dict) else 1.0,
                    "min_edges": int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
                    "max_edges": int(test_raw.get("max_edges", 6)) if isinstance(test_raw, dict) else 6,
                    "log_path": str(run_paths.observe_log),
                    "output_mode": output_mode,
                    "measure_path": str(run_paths.measure),
                    "test_limits": {
                        "min_freq_hz": test_raw.get("min_freq_hz") if isinstance(test_raw, dict) else None,
                        "max_freq_hz": test_raw.get("max_freq_hz") if isinstance(test_raw, dict) else None,
                        "duty_min": test_raw.get("duty_min") if isinstance(test_raw, dict) else None,
                        "duty_max": test_raw.get("duty_max") if isinstance(test_raw, dict) else None,
                    },
                },
            }
        )

    plan = {
        "version": "runplan/0.1",
        "plan_id": run_paths.run_id,
        "created_at": run_started.isoformat(),
        "inputs": {
            "board_id": board_id or "unknown",
            "probe_id": probe_cfg.get("name"),
            "instrument_id": (_resolve_instrument_context(test_raw, board_cfg)[0] if isinstance(test_raw, dict) else None),
            "test_id": Path(test_path).stem,
        },
        "selected": {
            "board_config": str(board_path) if board_path else "",
            "probe_config": str(probe_path) if probe_path else "",
            "test_config": str(test_path),
        },
        "context": {
            "workspace_dir": str(repo_root),
            "run_root": str(Path(repo_root) / "runs"),
            "artifact_root": str(Path(run_paths.root) / "artifacts"),
            "log_root": str(Path(run_paths.root)),
        },
        "preflight": {"checks": [{"type": "probe.health", "args": {}}], "policy": {"fail_fast": True}},
        "steps": plan_steps,
        "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"build": 1, "run": 2, "check": 2}},
        "report": {"emit": ["*.log", "*.json", "artifacts/*"]},
    }

    registry = AdapterRegistry()
    runner_result = run_plan(plan, Path(run_paths.root), registry)

    failed_step = _failed_step_name(runner_result)
    firmware_path = known_firmware_path or _extract_firmware_from_runner(runner_result)
    artifacts_copied = _copy_artifacts(firmware_path, run_paths.artifacts_dir)

    if _is_meter_digital_verify_test(test_raw):
        _write_json(run_paths.measure, {"ok": bool(runner_result.get("ok")), "type": "instrument_digital_verify"})

    result = {
        "ok": bool(runner_result.get("ok", False)),
        "failed_step": failed_step,
        "error_summary": runner_result.get("error_summary", ""),
        "logs": {
            "preflight": str(run_paths.preflight_log),
            "build": str(run_paths.build_log),
            "flash": str(run_paths.flash_log),
            "observe": str(run_paths.observe_log),
            "observe_uart": str(run_paths.observe_uart_step_log),
            "observe_uart_raw": str(run_paths.observe_uart_log),
            "verify": str(run_paths.verify_log),
        },
        "artifacts": artifacts_copied,
        "json": {
            "flash": str(run_paths.flash_json),
            "measure": str(run_paths.measure),
            "uart_observe": str(run_paths.uart_observe),
            "preflight": str(run_paths.preflight),
            "meta": str(run_paths.meta),
            "config_effective": str(run_paths.config_effective),
            "instrument_selftest": str(Path(run_paths.artifacts_dir) / "instrument_selftest.json"),
            "instrument_digital": str(Path(run_paths.artifacts_dir) / "instrument_digital.json"),
            "verify_result": str(Path(run_paths.artifacts_dir) / "verify_result.json"),
            "run_plan": str(Path(run_paths.artifacts_dir) / "run_plan.json"),
            "runner_result": str(Path(run_paths.artifacts_dir) / "result.json"),
        },
    }
    _write_json(run_paths.result, result)

    timings = {"total_s": round(time.monotonic() - run_started_mono, 3)}
    for s in ("preflight", "build", "load", "check_uart", "check_meter", "check_signal", "instrument_selftest"):
        entries = [x for x in runner_result.get("steps", []) if isinstance(x, dict) and x.get("name") == s]
        if entries:
            timings[f"{s}_attempts"] = len(entries)
    meta.update(
        {
            "ended_at": datetime.now().isoformat(),
            "timings": timings,
            "firmware": {"path": firmware_path, "sha256": _file_sha256(firmware_path) if firmware_path else ""},
            "runner_result": str(Path(run_paths.artifacts_dir) / "result.json"),
            "run_plan": str(Path(run_paths.artifacts_dir) / "run_plan.json"),
        }
    )
    _write_json(run_paths.meta, meta)

    if result["ok"]:
        print("PASS: Run verified")
        _emit_event(
            {
                "type": "run_succeeded",
                "severity": "info",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "verify",
                "summary": "run succeeded",
                "details": "",
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {
                    "build": str(run_paths.build_log),
                    "flash": str(run_paths.flash_log),
                    "observe": str(run_paths.observe_log),
                    "verify": str(run_paths.verify_log),
                    "uart": str(run_paths.observe_uart_log),
                },
            },
            notify_cfg,
        )
        return (0, run_paths) if return_paths else 0

    err_l = str(result["error_summary"]).lower()
    if "permission check failed" in err_l or "permission denied" in err_l:
        print("UART: permission check failed.")
        print("Action required: fix /dev/tty* permission/group manually, then rerun.")
    if "download mode" in err_l:
        print("UART: target entered bootloader download mode.")
        print("Action: reset DUT and rerun. Auto RTS reset was already attempted.")

    fail_stage = "verify"
    if failed_step.startswith("preflight"):
        fail_stage = "preflight"
    elif failed_step.startswith("build"):
        fail_stage = "build"
    elif failed_step.startswith("load"):
        fail_stage = "flash"
    elif failed_step.startswith("check_uart"):
        fail_stage = "observe_uart"
    _triage(fail_stage, {})

    _emit_event(
        {
            "type": "run_failed",
            "severity": "error",
            "run_id": run_paths.run_id,
            "dut": board_id or board_cfg.get("name", "unknown"),
            "bench": None,
            "step": failed_step or "runner",
            "summary": result.get("error_summary", "run failed"),
            "details": "",
            "artifacts_path": str(run_paths.root),
            "timestamp": datetime.now().isoformat(),
            "log_paths": {
                "preflight": str(run_paths.preflight_log),
                "build": str(run_paths.build_log),
                "flash": str(run_paths.flash_log),
                "observe": str(run_paths.observe_log),
                "verify": str(run_paths.verify_log),
                "uart": str(run_paths.observe_uart_log),
            },
        },
        notify_cfg,
    )
    code = _code_from_failed_step(failed_step)
    return (code, run_paths) if return_paths else code


def run(args):
    return run_pipeline(
        probe_path=args.probe,
        board_arg=args.board,
        test_path=args.test,
        wiring=args.wiring,
        output_mode=args.output_mode,
        skip_flash=args.skip_flash,
    )


def run_cli(probe_path, board_id, test_path, wiring=None, output_mode="normal"):
    return run_pipeline(
        probe_path=probe_path,
        board_arg=board_id,
        test_path=test_path,
        wiring=wiring,
        output_mode=output_mode,
    )


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--probe", required=True)
    run_p.add_argument("--board", required=True)
    run_p.add_argument("--test", required=False, default=os.path.join("tests", "blink_gpio.json"))
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--skip-flash", action="store_true")
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    args = parser.parse_args()
    if args.cmd == "run":
        if args.verbose:
            args.output_mode = "verbose"
        elif args.quiet:
            args.output_mode = "quiet"
        else:
            args.output_mode = "normal"
        code = run(args)
        sys.exit(code)


if __name__ == "__main__":
    main()
