import argparse
import json
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from adapters import (
    preflight,
    build_cmake,
    build_stm32,
    build_idf,
    flash_bmda_gdbmi,
    flash_idf,
    observe_gpio_pin,
    observe_uart_log,
    esp32s3_dev_c_meter_tcp,
)
from notifiers import discord_webhook
from ael import run_manager
from tools import la_verify

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
    if not cfg.get("gdb_cmd"):
        cfg["gdb_cmd"] = "gdb-multiarch"

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


def _default_firmware_path(target):
    root = os.path.dirname(__file__)
    if target.startswith("stm32"):
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
            print("Hint: GDB port closed. Check ESP32JTAG GDB server and IP/port.")
        if not pre_info.get("monitor_ok"):
            print("Hint: GDB server connected but monitor failed. Try power-cycle target and probe.")
        if not pre_info.get("la_ok"):
            print("Hint: LA web API failed. Check web credentials and HTTPS settings.")
        return
    if stage == "build":
        print("Hint: check pico-sdk path, CMake toolchain, and build dependencies.")
        return
    if stage == "flash":
        print("Hint: verify SWD wiring, target power, and only one GDB session connected.")
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

    test_raw = {}
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
    # Ensure all expected files exist even if we fail early.
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

    wiring_overrides = _parse_wiring(wiring or "")
    wiring_cfg = _merge_wiring(board_cfg.get("default_wiring", {}), wiring_overrides)
    wiring_cfg = _require_wiring(wiring_cfg, ["swd", "reset", "verify"])

    timings = {}
    result = {
        "ok": False,
        "failed_step": "",
        "error_summary": "",
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
        },
    }

    print("AI: starting pipeline")
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

    pre_info = {}
    with _tee_output(run_paths.preflight_log, output_mode):
        t0 = time.monotonic()
        ok_pre, pre_info = preflight.run(probe_cfg)
        timings["preflight_s"] = round(time.monotonic() - t0, 3)
    pre_info = pre_info or {}
    pre_info["timing_s"] = timings.get("preflight_s", 0)
    _write_json(run_paths.preflight, pre_info)

    if not ok_pre:
        result["failed_step"] = "preflight"
        result["error_summary"] = "preflight failed"
        _triage("preflight", pre_info)
        _write_json(run_paths.result, result)
        _emit_event(
            {
                "type": "run_failed",
                "severity": "error",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "preflight",
                "summary": "preflight failed",
                "details": "probe or LA not reachable",
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {"preflight": str(run_paths.preflight_log)},
            },
            notify_cfg,
        )
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return (2, run_paths) if return_paths else 2

    if _instrument_selftest_requested(test_raw, board_cfg):
        selftest_ok, selftest_artifact, selftest_error = _run_instrument_selftest(test_raw, board_cfg, run_paths)
        if selftest_artifact:
            result["artifacts"].append(selftest_artifact)
        if not selftest_ok:
            result["failed_step"] = "instrument_selftest"
            result["error_summary"] = selftest_error or "instrument selftest failed"
            _write_json(run_paths.result, result)
            _emit_event(
                {
                    "type": "run_failed",
                    "severity": "error",
                    "run_id": run_paths.run_id,
                    "dut": board_id or board_cfg.get("name", "unknown"),
                    "bench": None,
                    "step": "instrument_selftest",
                    "summary": "instrument selftest failed",
                    "details": result.get("error_summary"),
                    "artifacts_path": str(run_paths.root),
                    "timestamp": datetime.now().isoformat(),
                    "log_paths": {"preflight": str(run_paths.preflight_log)},
                },
                notify_cfg,
            )
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return (7, run_paths) if return_paths else 7

    print("SWD and network connection verified. Starting task.")
    if not pre_info.get("targets"):
        print("Preflight: warning - no targets reported by probe.")

    firmware_path = None
    if verify_only:
        timings["build_s"] = 0.0
    elif no_build:
        target = board_cfg.get("target", "")
        firmware_path = _default_firmware_path(target)
        if not os.path.exists(firmware_path):
            result["failed_step"] = "build"
            result["error_summary"] = "no build artifacts found"
            _write_json(run_paths.result, result)
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return (3, run_paths) if return_paths else 3
        timings["build_s"] = 0.0
    else:
        with _tee_output(run_paths.build_log, output_mode):
            t0 = time.monotonic()
            target = board_cfg.get("target", "")
            build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg, dict) else {}
            build_type = build_cfg.get("type", "")
            if build_type == "idf":
                firmware_path = build_idf.run(board_cfg)
            elif target.startswith("stm32"):
                firmware_path = build_stm32.run(board_cfg)
            else:
                firmware_path = build_cmake.run(board_cfg)
            timings["build_s"] = round(time.monotonic() - t0, 3)

    if (not verify_only) and (not firmware_path):
        result["failed_step"] = "build"
        result["error_summary"] = "build failed"
        _triage("build", pre_info)
        _write_json(run_paths.result, result)
        _emit_event(
            {
                "type": "run_failed",
                "severity": "error",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "build",
                "summary": "build failed",
                "details": result.get("error_summary"),
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {"build": str(run_paths.build_log)},
            },
            notify_cfg,
        )
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return (3, run_paths) if return_paths else 3

    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg, dict) else {}
    reset_unwired = wiring_cfg.get("reset") in ("NC", "NONE", "NONE/NC", "N/C", "NA")
    if reset_unwired:
        flash_cfg = dict(flash_cfg)
        flash_cfg["reset_available"] = False
    if verify_only:
        timings["flash_s"] = 0.0
    elif skip_flash:
        with _tee_output(run_paths.flash_log, output_mode):
            print("Flash: SKIPPED (user requested skip)")
        _write_json(
            run_paths.flash_json,
            {"ok": False, "attempts": [], "strategy_used": "skipped", "speed_khz": flash_cfg.get("speed_khz")},
        )
        timings["flash_s"] = 0.0
    else:
        with _tee_output(run_paths.flash_log, output_mode):
            t0 = time.monotonic()
            method = flash_cfg.get("method", "")
            if method == "idf_esptool":
                # pass project_dir for IDF flash
                if board_cfg.get("build", {}):
                    flash_cfg = dict(flash_cfg)
                    flash_cfg["project_dir"] = board_cfg.get("build", {}).get("project_dir")
                target = board_cfg.get("target")
                if target:
                    flash_cfg = dict(flash_cfg)
                    flash_cfg["target"] = target
                    flash_cfg["build_dir"] = os.path.join(repo_root, "artifacts", f"build_{target}")
                flash_ok = flash_idf.run(
                    probe_cfg,
                    firmware_path,
                    flash_cfg=flash_cfg,
                    flash_json_path=str(run_paths.flash_json),
                )
            else:
                flash_ok = flash_bmda_gdbmi.run(
                    probe_cfg,
                    firmware_path,
                    flash_cfg=flash_cfg,
                    flash_json_path=str(run_paths.flash_json),
                )
            timings["flash_s"] = round(time.monotonic() - t0, 3)

        if not flash_ok:
            result["failed_step"] = "flash"
            result["error_summary"] = "flash failed"
            _triage("flash", pre_info)
            _write_json(run_paths.result, result)
            _emit_event(
                {
                    "type": "run_failed",
                    "severity": "error",
                    "run_id": run_paths.run_id,
                    "dut": board_id or board_cfg.get("name", "unknown"),
                    "bench": None,
                    "step": "flash",
                    "summary": "flash failed",
                    "details": result.get("error_summary"),
                    "artifacts_path": str(run_paths.root),
                    "timestamp": datetime.now().isoformat(),
                    "log_paths": {"flash": str(run_paths.flash_log)},
                },
                notify_cfg,
            )
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return (4, run_paths) if return_paths else 4

    capture = {}
    observe_uart_cfg = {}
    if isinstance(effective, dict):
        observe_uart_cfg = effective.get("observe_uart", {}) or {}
    if isinstance(observe_uart_cfg, dict) and observe_uart_cfg.get("enabled"):
        if not observe_uart_cfg.get("port"):
            try:
                with open(run_paths.flash_json, "r", encoding="utf-8") as f:
                    flash_info = json.load(f)
                if flash_info.get("port"):
                    observe_uart_cfg = dict(observe_uart_cfg)
                    observe_uart_cfg["port"] = flash_info.get("port")
            except Exception:
                pass
        with _tee_output(run_paths.observe_uart_step_log, output_mode):
            uart_result = observe_uart_log.run(observe_uart_cfg, raw_log_path=str(run_paths.observe_uart_log))
        _write_json(run_paths.uart_observe, uart_result)
        result["uart"] = uart_result
        if not uart_result.get("ok", True):
            result["failed_step"] = "observe_uart"
            result["error_summary"] = uart_result.get("error_summary") or "uart observe failed"
            _triage("observe_uart", pre_info)
            _write_json(run_paths.result, result)
            _emit_event(
                {
                    "type": "run_failed",
                    "severity": "error",
                    "run_id": run_paths.run_id,
                    "dut": board_id or board_cfg.get("name", "unknown"),
                    "bench": None,
                    "step": "observe_uart",
                    "summary": result.get("error_summary"),
                    "details": "",
                    "artifacts_path": str(run_paths.root),
                    "timestamp": datetime.now().isoformat(),
                    "log_paths": {"uart": str(run_paths.observe_uart_log)},
                },
                notify_cfg,
            )
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return (5, run_paths) if return_paths else 5
    observe_map = board_cfg.get("observe_map", {}) if isinstance(board_cfg, dict) else {}
    test_pin = test_raw.get("pin") if isinstance(test_raw, dict) else None
    pin_value = test_pin
    if test_pin and isinstance(observe_map, dict) and test_pin in observe_map:
        pin_value = observe_map.get(test_pin)
    if not pin_value:
        pin_value = wiring_cfg.get("verify")

    if isinstance(test_raw, dict) and test_raw.get("sample_rate_hz"):
        probe_cfg["la_sample_rate"] = int(test_raw.get("sample_rate_hz"))
    if isinstance(test_raw, dict) and test_raw.get("duration_ms") and not test_raw.get("duration_s"):
        test_raw["duration_s"] = float(test_raw.get("duration_ms")) / 1000.0

    with _tee_output(run_paths.observe_log, output_mode):
        t0 = time.monotonic()
        ok_obs = observe_gpio_pin.run(
            probe_cfg,
            pin=pin_value,
            duration_s=float(test_raw.get("duration_s", 3.0)) if isinstance(test_raw, dict) else 3.0,
            expected_hz=float(test_raw.get("expected_hz", 1.0)) if isinstance(test_raw, dict) else 1.0,
            min_edges=int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
            max_edges=int(test_raw.get("max_edges", 6)) if isinstance(test_raw, dict) else 6,
            capture_out=capture,
            verify_edges=False,
        )
        timings["observe_s"] = round(time.monotonic() - t0, 3)

    if not ok_obs:
        result["failed_step"] = "observe"
        result["error_summary"] = "observe failed"
        _write_json(run_paths.result, result)
        _emit_event(
            {
                "type": "run_failed",
                "severity": "error",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "observe",
                "summary": result.get("error_summary"),
                "details": "",
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {"observe": str(run_paths.observe_log)},
            },
            notify_cfg,
        )
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return (5, run_paths) if return_paths else 5

    measure = {}
    verify_ok = False
    with _tee_output(run_paths.verify_log, output_mode):
        t0 = time.monotonic()
        if capture.get("blob"):
            measure = la_verify.analyze_capture_bytes(
                capture.get("blob"),
                int(capture.get("sample_rate_hz", 0)),
                int(capture.get("bit", 0)),
                min_edges=int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
            )
            verify_ok = bool(measure.get("ok"))
            metrics = measure.get("metrics", {})
            print(
                "Verify: freq={:.3f}Hz duty={:.3f} jitter_est={:.6f}s".format(
                    metrics.get("freq_hz", 0.0),
                    metrics.get("duty", 0.0),
                    metrics.get("jitter_est", 0.0),
                )
            )
            if isinstance(test_raw, dict):
                min_f = test_raw.get("min_freq_hz")
                max_f = test_raw.get("max_freq_hz")
                duty_min = test_raw.get("duty_min")
                duty_max = test_raw.get("duty_max")
                if min_f is not None and metrics.get("freq_hz", 0.0) < float(min_f):
                    measure.setdefault("reasons", []).append("freq_below_min")
                    verify_ok = False
                if max_f is not None and metrics.get("freq_hz", 0.0) > float(max_f):
                    measure.setdefault("reasons", []).append("freq_above_max")
                    verify_ok = False
                if duty_min is not None and metrics.get("duty", 0.0) < float(duty_min):
                    measure.setdefault("reasons", []).append("duty_below_min")
                    verify_ok = False
                if duty_max is not None and metrics.get("duty", 0.0) > float(duty_max):
                    measure.setdefault("reasons", []).append("duty_above_max")
                    verify_ok = False

            measure["ok"] = bool(verify_ok)
            if not verify_ok:
                print("Verify: FAIL " + ", ".join(measure.get("reasons", [])))
        else:
            measure = {"ok": False, "metrics": {}, "reasons": ["no_capture"]}
            verify_ok = False
            print("Verify: FAIL no capture")
        timings["verify_s"] = round(time.monotonic() - t0, 3)

    _write_json(run_paths.measure, measure)

    if not verify_ok:
        result["failed_step"] = "verify"
        result["error_summary"] = "verify failed"
        _triage("verify", pre_info)
        if reset_unwired:
            print("Hint: reset line not wired. Power-cycle target and rerun verify.")
        _write_json(run_paths.result, result)
        _emit_event(
            {
                "type": "run_failed",
                "severity": "error",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "verify",
                "summary": result.get("error_summary"),
                "details": ",".join(measure.get("reasons", [])) if isinstance(measure, dict) else "",
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {"verify": str(run_paths.verify_log)},
            },
            notify_cfg,
        )
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return (6, run_paths) if return_paths else 6

    timings["total_s"] = round(time.monotonic() - run_started_mono, 3)

    artifacts_copied = _copy_artifacts(firmware_path, run_paths.artifacts_dir)

    print("PASS: Blink verified")
    print(
        "Summary: "
        f"preflight={timings.get('preflight_s', 0)}s "
        f"build={timings.get('build_s', 0)}s "
        f"flash={timings.get('flash_s', 0)}s "
        f"observe={timings.get('observe_s', 0)}s "
        f"verify={timings.get('verify_s', 0)}s "
        f"total={timings.get('total_s', 0)}s"
    )

    result["ok"] = True
    result["failed_step"] = ""
    result["error_summary"] = ""
    existing_artifacts = result.get("artifacts", [])
    if not isinstance(existing_artifacts, list):
        existing_artifacts = []
    result["artifacts"] = existing_artifacts + artifacts_copied
    _write_json(run_paths.result, result)

    meta.update(
        {
            "ended_at": datetime.now().isoformat(),
            "timings": timings,
            "firmware": {
                "path": firmware_path,
                "sha256": _file_sha256(firmware_path) if firmware_path else "",
            },
        }
    )
    _write_json(run_paths.meta, meta)

    print(f"Run metadata saved: {run_paths.meta}")
    print(f"Run log saved: {run_paths.build_log}")
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
