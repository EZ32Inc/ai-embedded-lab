from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ael.adapters import build_artifacts


@dataclass(frozen=True)
class ResolvedRunStrategy:
    probe_cfg: Dict[str, Any]
    board_cfg: Dict[str, Any]
    wiring_cfg: Dict[str, Any]
    timeout_s: Optional[float]
    test_name: Optional[str]
    instrument_id: Optional[str]
    instrument_host: Optional[str]
    instrument_port: Optional[int]


def normalize_probe_cfg(raw: Dict[str, Any] | Any) -> Dict[str, Any]:
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


def resolve_run_timeout_s(test_raw: Dict[str, Any] | Any, request_timeout_s: Optional[float] = None) -> Optional[float]:
    if request_timeout_s is not None:
        try:
            return max(0.0, float(request_timeout_s))
        except Exception:
            return None
    if isinstance(test_raw, dict):
        run_cfg = test_raw.get("run", {})
        if isinstance(run_cfg, dict) and run_cfg.get("timeout_s") is not None:
            try:
                return max(0.0, float(run_cfg.get("timeout_s")))
            except Exception:
                return None
        if test_raw.get("timeout_s") is not None:
            try:
                return max(0.0, float(test_raw.get("timeout_s")))
            except Exception:
                return None
    return None


def _parse_wiring(s: Optional[str]) -> Dict[str, str]:
    wiring: Dict[str, str] = {}
    if not s:
        return wiring
    parts = [p.strip() for p in str(s).split() if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        wiring[k.strip()] = v.strip()
    return wiring


def _merge_wiring(defaults: Dict[str, Any] | Any, overrides: Dict[str, Any] | Any) -> Dict[str, Any]:
    merged = dict(defaults or {})
    merged.update(overrides or {})
    return merged


def _require_wiring(merged: Dict[str, Any], required: list[str]) -> Dict[str, Any]:
    missing = [k for k in required if k not in merged or not merged[k]]
    if missing:
        for k in missing:
            merged[k] = "UNKNOWN"
    return merged


def resolve_instrument_context(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any):
    explicit: Dict[str, Any] = {}
    if isinstance(test_raw, dict):
        explicit = test_raw.get("instrument", {}) if isinstance(test_raw.get("instrument"), dict) else {}
    if not explicit and isinstance(board_cfg, dict):
        explicit = board_cfg.get("instrument", {}) if isinstance(board_cfg.get("instrument"), dict) else {}
    instrument_id = explicit.get("id")
    if not instrument_id:
        return None, {}, {}

    manifest: Dict[str, Any] = {}
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
                hint = t.get("endpoint_hint")
                if hint and ":" in str(hint):
                    host, port = str(hint).rsplit(":", 1)
                    try:
                        endpoint = {"host": host.strip(), "port": int(port.strip())}
                    except Exception:
                        endpoint = {}
                if endpoint:
                    break
        wifi_cfg = manifest.get("wifi", {}) if isinstance(manifest.get("wifi"), dict) else {}
        host = tcp_cfg.get("host") or endpoint.get("host") or wifi_cfg.get("ap_ip")
        port = tcp_cfg.get("port") or endpoint.get("port") or wifi_cfg.get("tcp_port")
        tcp_cfg = {"host": host, "port": port}

    return instrument_id, tcp_cfg, manifest


def resolve_bench_setup(test_raw: Dict[str, Any] | Any) -> Dict[str, Any]:
    if not isinstance(test_raw, dict):
        return {}
    bench_setup = test_raw.get("bench_setup")
    if isinstance(bench_setup, dict) and bench_setup:
        return bench_setup
    legacy = test_raw.get("connections", {})
    if isinstance(legacy, dict):
        return legacy
    if isinstance(bench_setup, dict):
        return bench_setup
    return {}


def instrument_selftest_requested(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any) -> bool:
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


def is_meter_digital_verify_test(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any) -> bool:
    if not isinstance(test_raw, dict):
        return False
    inst = test_raw.get("instrument", {})
    if not isinstance(inst, dict):
        return False
    instrument_id = str(inst.get("id") or "").strip()
    if not instrument_id:
        return False
    _, _, manifest = resolve_instrument_context(test_raw, board_cfg)
    caps = manifest.get("capabilities", []) if isinstance(manifest, dict) else []
    has_measure_digital = any(isinstance(c, dict) and c.get("name") == "measure.digital" for c in caps)
    if not has_measure_digital:
        return False
    conns = resolve_bench_setup(test_raw)
    if not isinstance(conns, dict):
        return False
    links = conns.get("dut_to_instrument", [])
    return isinstance(links, list) and len(links) > 0


def resolve_builder_kind(board_cfg: Dict[str, Any] | Any) -> str:
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


def default_firmware_path(repo_root: Path, board_cfg: Dict[str, Any] | Any) -> str:
    return build_artifacts.default_firmware_path(repo_root, board_cfg, resolve_builder_kind(board_cfg))


def resolve_run_strategy(
    probe_raw: Dict[str, Any] | Any,
    board_raw: Dict[str, Any] | Any,
    test_raw: Dict[str, Any] | Any,
    wiring: Optional[str],
    request_timeout_s: Optional[float],
    repo_root: Path,
) -> ResolvedRunStrategy:
    probe_cfg = normalize_probe_cfg(probe_raw)
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

    wiring_overrides = _parse_wiring(wiring)
    wiring_cfg = _merge_wiring(board_cfg.get("default_wiring", {}), wiring_overrides)
    wiring_cfg = _require_wiring(wiring_cfg, ["swd", "reset", "verify"])
    timeout_s = resolve_run_timeout_s(test_raw, request_timeout_s=request_timeout_s)

    test_name = test_raw.get("name") if isinstance(test_raw, dict) else None
    instrument_cfg = test_raw.get("instrument", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("instrument"), dict) else {}
    instrument_id = instrument_cfg.get("id")
    instrument_host = instrument_cfg.get("tcp", {}).get("host") if isinstance(instrument_cfg.get("tcp"), dict) else None
    instrument_port = instrument_cfg.get("tcp", {}).get("port") if isinstance(instrument_cfg.get("tcp"), dict) else None
    return ResolvedRunStrategy(
        probe_cfg=probe_cfg,
        board_cfg=board_cfg,
        wiring_cfg=wiring_cfg,
        timeout_s=timeout_s,
        test_name=test_name,
        instrument_id=instrument_id,
        instrument_host=instrument_host,
        instrument_port=instrument_port,
    )


def build_preflight_step(test_raw: Dict[str, Any] | Any, probe_cfg: Dict[str, Any], out_json: str, output_mode: str, log_path: str):
    preflight_cfg = test_raw.get("preflight", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("preflight"), dict) else {}
    preflight_enabled = True if preflight_cfg.get("enabled") is None else bool(preflight_cfg.get("enabled"))
    if not preflight_enabled:
        return None
    return {
        "name": "preflight",
        "type": "preflight.probe",
        "inputs": {
            "probe_cfg": probe_cfg,
            "out_json": out_json,
            "output_mode": output_mode,
            "log_path": log_path,
        },
    }


def build_instrument_selftest_step(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any, artifacts_dir: Path):
    if not instrument_selftest_requested(test_raw, board_cfg):
        return None
    instrument_id, tcp_cfg, manifest = resolve_instrument_context(test_raw, board_cfg)
    selftest_manifest = manifest.get("selftest", {}) if isinstance(manifest, dict) else {}
    dig = selftest_manifest.get("digital", {}) if isinstance(selftest_manifest.get("digital"), dict) else {}
    adc = selftest_manifest.get("adc", {}) if isinstance(selftest_manifest.get("adc"), dict) else {}
    test_self = test_raw.get("selftest", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("selftest"), dict) else {}
    test_dig = test_self.get("digital", {}) if isinstance(test_self.get("digital"), dict) else {}
    test_adc = test_self.get("adc", {}) if isinstance(test_self.get("adc"), dict) else {}
    return {
        "name": "instrument_selftest",
        "type": "check.instrument_selftest",
        "inputs": {
            "instrument_id": instrument_id,
            "cfg": {
                "host": tcp_cfg.get("host"),
                "port": int(tcp_cfg.get("port")) if tcp_cfg.get("port") is not None else 9000,
                "artifacts_dir": str(artifacts_dir),
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
            "out_path": str(artifacts_dir / "instrument_selftest.json"),
        },
    }


def resolve_build_stage(
    board_cfg: Dict[str, Any] | Any,
    verify_only: bool,
    no_build: bool,
    repo_root: Path,
    output_mode: str,
    build_log_path: str,
):
    build_kind = resolve_builder_kind(board_cfg)
    known_firmware_path = None
    build_step = None
    if not verify_only and not no_build:
        build_step = {
            "name": "build",
            "type": f"build.{build_kind}",
            "inputs": {
                "board_cfg": board_cfg,
                "output_mode": output_mode,
                "log_path": build_log_path,
            },
        }
    elif not verify_only and no_build:
        known_firmware_path = default_firmware_path(repo_root, board_cfg)
    return build_kind, known_firmware_path, build_step


def resolve_load_stage(
    board_cfg: Dict[str, Any] | Any,
    wiring_cfg: Dict[str, Any] | Any,
    probe_cfg: Dict[str, Any] | Any,
    known_firmware_path: Optional[str],
    verify_only: bool,
    skip_flash: bool,
    repo_root: Path,
    output_mode: str,
    flash_json_path: str,
    flash_log_path: str,
):
    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg, dict) else {}
    reset_unwired = wiring_cfg.get("reset") in ("NC", "NONE", "NONE/NC", "N/C", "NA")
    if reset_unwired:
        flash_cfg = dict(flash_cfg)
        flash_cfg["reset_available"] = False
    if verify_only or skip_flash:
        return None, flash_cfg

    method = str(flash_cfg.get("method", "gdbmi")).strip()
    if method == "idf_esptool":
        if board_cfg.get("build", {}):
            flash_cfg = dict(flash_cfg)
            flash_cfg["project_dir"] = board_cfg.get("build", {}).get("project_dir")
        target = board_cfg.get("target")
        if target:
            flash_cfg = dict(flash_cfg)
            flash_cfg["target"] = target
            flash_cfg["build_dir"] = os.path.join(str(repo_root), "artifacts", f"build_{target}")
    step = {
        "name": "load",
        "type": "load.idf_esptool" if method == "idf_esptool" else "load.gdbmi",
        "inputs": {
            "probe_cfg": probe_cfg,
            "firmware_path": known_firmware_path,
            "flash_cfg": flash_cfg,
            "flash_json_path": flash_json_path,
            "output_mode": output_mode,
            "log_path": flash_log_path,
        },
    }
    return step, flash_cfg


def build_uart_step(effective: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any, output_mode: str, observe_uart_log: str, uart_json: str, flash_json: str, observe_uart_step_log: str):
    observe_uart_cfg = {}
    if isinstance(effective, dict):
        observe_uart_cfg = effective.get("observe_uart", {}) or {}
    if not (isinstance(observe_uart_cfg, dict) and observe_uart_cfg.get("enabled")):
        return None
    observe_uart_cfg = dict(observe_uart_cfg)
    observe_uart_cfg.setdefault("auto_reset_on_download", True)
    observe_uart_cfg.setdefault("reset_strategy", board_cfg.get("uart_reset_strategy", "none"))
    step = {
        "name": "check_uart",
        "type": "check.uart_log",
        "inputs": {
            "observe_uart_cfg": observe_uart_cfg,
            "raw_log_path": observe_uart_log,
            "out_json": uart_json,
            "flash_json_path": flash_json,
            "output_mode": output_mode,
            "log_path": observe_uart_step_log,
        },
    }
    recovery_demo = observe_uart_cfg.get("recovery_demo", {}) if isinstance(observe_uart_cfg.get("recovery_demo"), dict) else {}
    if bool(recovery_demo.get("fail_first")):
        step["retry_budget"] = 0
        step["rewind_anchor"] = "check_uart"
    return step


def build_verify_step(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any, probe_cfg: Dict[str, Any] | Any, wiring_cfg: Dict[str, Any] | Any, artifacts_dir: Path, observe_log: str, output_mode: str, measure_path: str):
    if is_meter_digital_verify_test(test_raw, board_cfg):
        instrument_id, tcp_cfg, _manifest = resolve_instrument_context(test_raw, board_cfg)
        bench_setup = resolve_bench_setup(test_raw)
        links = bench_setup.get("dut_to_instrument", [])
        analog_links = bench_setup.get("dut_to_instrument_analog", [])
        duration_ms = 500
        meas_cfg = test_raw.get("measurement", {})
        if isinstance(meas_cfg, dict) and meas_cfg.get("duration_ms") is not None:
            duration_ms = int(meas_cfg.get("duration_ms"))
        return {
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
                "digital_out": str(artifacts_dir / "instrument_digital.json"),
                "verify_out": str(artifacts_dir / "verify_result.json"),
                "analog_out": str(artifacts_dir / "instrument_voltage.json"),
            },
        }

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
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": check_probe_cfg,
            "pin": pin_value,
            "duration_s": duration_s,
            "expected_hz": float(test_raw.get("expected_hz", 1.0)) if isinstance(test_raw, dict) else 1.0,
            "min_edges": int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
            "max_edges": int(test_raw.get("max_edges", 6)) if isinstance(test_raw, dict) else 6,
            "log_path": observe_log,
            "output_mode": output_mode,
            "measure_path": measure_path,
            "test_limits": {
                "min_freq_hz": test_raw.get("min_freq_hz") if isinstance(test_raw, dict) else None,
                "max_freq_hz": test_raw.get("max_freq_hz") if isinstance(test_raw, dict) else None,
                "duty_min": test_raw.get("duty_min") if isinstance(test_raw, dict) else None,
                "duty_max": test_raw.get("duty_max") if isinstance(test_raw, dict) else None,
            },
            "recovery_demo": (test_raw.get("recovery_demo", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("recovery_demo"), dict) else {}),
        },
    }
    recovery_demo = step["inputs"].get("recovery_demo", {})
    if isinstance(recovery_demo, dict) and bool(recovery_demo.get("fail_first")):
        # Ensure runner reaches recovery flow immediately on first injected failure.
        step["retry_budget"] = 0
        step["rewind_anchor"] = "check_signal"
    return step
