from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ael.adapters import build_artifacts
from ael.bench_profile_loader import resolve_bench_wiring_fields
from ael.compatibility.model import CompatibilityResult
from ael.compatibility.resolver import resolve_test_instrument
from ael.connection_model import NormalizedConnectionContext, normalize_connection_context, resolve_bench_setup, _as_board_dict


@dataclass(frozen=True)
class ResolvedRunStrategy:
    probe_cfg: Dict[str, Any]
    board_cfg: Dict[str, Any]
    wiring_cfg: Dict[str, Any]
    connection_ctx: NormalizedConnectionContext
    timeout_s: Optional[float]
    test_name: Optional[str]
    instrument_id: Optional[str]
    instrument_host: Optional[str]
    instrument_port: Optional[int]
    instrument_communication: Dict[str, Any]
    instrument_capability_surfaces: Dict[str, str]
    compatibility_result: Optional[CompatibilityResult] = None


def normalize_probe_cfg(raw: Dict[str, Any] | Any) -> Dict[str, Any]:
    probe = raw.get("probe", {}) if isinstance(raw, dict) else {}
    connection = raw.get("connection", {}) if isinstance(raw, dict) else {}
    instance = raw.get("instance", {}) if isinstance(raw, dict) else {}
    communication = raw.get("communication", {}) if isinstance(raw, dict) else {}
    capability_surfaces = raw.get("capability_surfaces", {}) if isinstance(raw, dict) else {}
    preflight = raw.get("preflight", {}) if isinstance(raw, dict) else {}
    cfg = dict(probe)
    if "ip" not in cfg and "ip" in connection:
        cfg["ip"] = connection["ip"]
    if "gdb_port" not in cfg and "gdb_port" in connection:
        cfg["gdb_port"] = connection["gdb_port"]
    if "gdb_cmd" not in cfg:
        cfg["gdb_cmd"] = raw.get("gdb_cmd") if isinstance(raw, dict) else None
    if isinstance(instance, dict):
        if "instance_id" not in cfg and instance.get("id") is not None:
            cfg["instance_id"] = instance.get("id")
        if "type_id" not in cfg and instance.get("type") is not None:
            cfg["type_id"] = instance.get("type")
        if "name" not in cfg:
            label = instance.get("label")
            inst_type = instance.get("type")
            cfg["name"] = label or inst_type or cfg.get("name")
    if isinstance(communication, dict) and communication and "communication" not in cfg:
        cfg["communication"] = dict(communication)
    if isinstance(capability_surfaces, dict) and capability_surfaces and "capability_surfaces" not in cfg:
        cfg["capability_surfaces"] = dict(capability_surfaces)
    if isinstance(preflight, dict) and preflight and "preflight" not in cfg:
        cfg["preflight"] = dict(preflight)
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

def _normalize_communication_metadata(payload: Dict[str, Any] | Any) -> Dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("communication"), dict):
        return dict(payload.get("communication") or {})
    return {}


def _normalize_capability_surfaces(payload: Dict[str, Any] | Any) -> Dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("capability_surfaces")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in raw.items():
        cap = str(key).strip()
        surface = str(value).strip() if value is not None else ""
        if cap and surface:
            out[cap] = surface
    return out


def resolve_control_instrument_override(repo_root: Path, test_raw: Dict[str, Any] | Any) -> Tuple[Optional[str], Optional[str]]:
    bench_setup = resolve_bench_setup(test_raw)
    if not isinstance(bench_setup, dict):
        return None, None
    for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").strip() != "control_instrument":
            continue
        instance_id = str(item.get("instrument_id") or "").strip() or None
        if not instance_id:
            return None, None
        rel = os.path.join("configs", "instrument_instances", f"{instance_id}.yaml")
        return instance_id, (rel if (repo_root / rel).exists() else None)
    return None, None


def resolve_instrument_context(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any):
    board_cfg = _as_board_dict(board_cfg)
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

def instrument_selftest_requested(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any) -> bool:
    board_cfg = _as_board_dict(board_cfg)
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
    board_cfg = _as_board_dict(board_cfg)
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
    board_cfg = _as_board_dict(board_cfg)
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
    board_cfg = _as_board_dict(board_cfg)
    return build_artifacts.default_firmware_path(repo_root, board_cfg, resolve_builder_kind(board_cfg))


def resolve_run_strategy(
    probe_raw: Dict[str, Any] | Any,
    board_raw: Dict[str, Any] | Any,
    test_raw: Dict[str, Any] | Any,
    wiring: Optional[str],
    request_timeout_s: Optional[float],
    repo_root: Path,
    pack_meta: Optional[Dict[str, Any]] = None,
) -> ResolvedRunStrategy:
    probe_cfg = normalize_probe_cfg(probe_raw)
    if hasattr(board_raw, "to_legacy_dict"):
        board_cfg = board_raw.to_legacy_dict()
    elif isinstance(board_raw, dict):
        raw_board = board_raw.get("board", {})
        board_cfg = dict(raw_board) if isinstance(raw_board, dict) else {}
    else:
        board_cfg = {}
    bench_fields = resolve_bench_wiring_fields(str(repo_root), board_raw if isinstance(board_raw, dict) else {}, pack_meta=pack_meta)
    board_cfg.update(bench_fields)

    test_build = test_raw.get("build", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("build"), dict) else {}
    firmware_override = test_raw.get("firmware") if isinstance(test_raw, dict) else None
    project_override = test_build.get("project_dir") or firmware_override
    if project_override or test_build:
        build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
        build_cfg = dict(build_cfg)
        if project_override:
            build_cfg["project_dir"] = str(project_override)
        for key in ("type", "artifact_stem", "build_dir", "target"):
            value = test_build.get(key)
            if value not in (None, ""):
                build_cfg[key] = value
        board_cfg["build"] = build_cfg

    connection_ctx = normalize_connection_context(
        board_cfg,
        test_raw,
        wiring=wiring,
        required_wiring=["swd", "reset", "verify"],
    )
    wiring_cfg = dict(connection_ctx.resolved_wiring)
    timeout_s = resolve_run_timeout_s(test_raw, request_timeout_s=request_timeout_s)

    test_name = test_raw.get("name") if isinstance(test_raw, dict) else None
    instrument_id, instrument_tcp_cfg, instrument_manifest = resolve_instrument_context(test_raw, board_cfg)
    instrument_host = instrument_tcp_cfg.get("host") if isinstance(instrument_tcp_cfg, dict) else None
    instrument_port = instrument_tcp_cfg.get("port") if isinstance(instrument_tcp_cfg, dict) else None

    required_capabilities = (
        list(test_raw.get("required_capabilities") or [])
        if isinstance(test_raw, dict) else []
    )
    probe_surfaces = _normalize_capability_surfaces(probe_raw)
    compatibility_result: Optional[CompatibilityResult] = None
    if required_capabilities:
        compatibility_result = resolve_test_instrument(required_capabilities, probe_surfaces)

    return ResolvedRunStrategy(
        probe_cfg=probe_cfg,
        board_cfg=board_cfg,
        wiring_cfg=wiring_cfg,
        connection_ctx=connection_ctx,
        timeout_s=timeout_s,
        test_name=test_name,
        instrument_id=instrument_id,
        instrument_host=instrument_host,
        instrument_port=instrument_port,
        instrument_communication=_normalize_communication_metadata(instrument_manifest),
        instrument_capability_surfaces=_normalize_capability_surfaces(instrument_manifest),
        compatibility_result=compatibility_result,
    )


def build_preflight_step(test_raw: Dict[str, Any] | Any, probe_cfg: Dict[str, Any], out_json: str, output_mode: str, log_path: str):
    preflight_cfg = test_raw.get("preflight", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("preflight"), dict) else {}
    preflight_enabled = True if preflight_cfg.get("enabled") is None else bool(preflight_cfg.get("enabled"))
    if not preflight_enabled:
        return None
    bench_setup = resolve_bench_setup(test_raw)
    return {
        "name": "preflight",
        "type": "preflight.probe",
        "inputs": {
            "probe_cfg": probe_cfg,
            "bench_setup": bench_setup,
            "out_json": out_json,
            "output_mode": output_mode,
            "log_path": log_path,
        },
    }


def build_instrument_selftest_step(test_raw: Dict[str, Any] | Any, board_cfg: Dict[str, Any] | Any, artifacts_dir: Path):
    board_cfg = _as_board_dict(board_cfg)
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
    board_cfg = _as_board_dict(board_cfg)
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
    board_cfg = _as_board_dict(board_cfg)
    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg, dict) else {}
    reset_unwired = wiring_cfg.get("reset") in ("NC", "NONE", "NONE/NC", "N/C", "NA")
    if reset_unwired:
        flash_cfg = dict(flash_cfg)
        flash_cfg["reset_available"] = False
    if verify_only or skip_flash:
        return None, flash_cfg

    method = str(flash_cfg.get("method", "gdbmi")).strip()
    flash_cfg = dict(flash_cfg)
    flash_cfg["flash_log_path"] = flash_log_path
    if method == "idf_esptool":
        if board_cfg.get("build", {}):
            flash_cfg["project_dir"] = board_cfg.get("build", {}).get("project_dir")
        target = board_cfg.get("target")
        if target:
            flash_cfg["target"] = target
            build_dir_override = board_cfg.get("build", {}).get("build_dir")
            if build_dir_override:
                flash_cfg["build_dir"] = os.path.join(str(repo_root), build_dir_override)
            else:
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
    board_cfg = _as_board_dict(board_cfg)
    observe_uart_cfg = {}
    if isinstance(effective, dict):
        observe_uart_cfg = effective.get("observe_uart", {}) or {}
    if not (isinstance(observe_uart_cfg, dict) and observe_uart_cfg.get("enabled")):
        return None
    observe_uart_cfg = dict(observe_uart_cfg)
    bench_setup = resolve_bench_setup(effective)
    if isinstance(bench_setup, dict):
        serial_console = bench_setup.get("serial_console")
        if isinstance(serial_console, dict):
            serial_port = str(serial_console.get("port") or "").strip()
            if serial_port and not str(observe_uart_cfg.get("port") or "").strip():
                observe_uart_cfg["port"] = serial_port
            if observe_uart_cfg.get("baud") is None and serial_console.get("baud") is not None:
                observe_uart_cfg["baud"] = serial_console.get("baud")
        for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
            if not isinstance(item, dict):
                continue
            if str(item.get("role") or "").strip() != "uart_instrument":
                continue
            endpoint = str(item.get("endpoint") or "").strip()
            instrument_id = str(item.get("instrument_id") or "").strip()
            if endpoint:
                observe_uart_cfg.setdefault("bridge_endpoint", endpoint)
            if instrument_id:
                observe_uart_cfg.setdefault("bridge_instrument_id", instrument_id)
            break
    # Detect native-USB-only boards (no USB-UART bridge chip).
    # On these boards RTS/DTR lines do NOT control reset or boot mode.
    # Indicators: console.type==usb_serial_jtag OR console.rts_dtr_reset==False.
    # Force reset_strategy=none to prevent AEL from attempting RTS/DTR resets.
    board_console = board_cfg.get("console", {}) or {}
    _native_usb = (
        str(board_console.get("type") or "").lower() == "usb_serial_jtag"
        or not bool(board_console.get("rts_dtr_reset", True))
        or str(board_cfg.get("usb_interface_type") or "").lower() == "native_only"
    )
    if _native_usb:
        observe_uart_cfg["reset_strategy"] = "none"
        observe_uart_cfg["auto_reset_on_download"] = False
    else:
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
    board_cfg = _as_board_dict(board_cfg)
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
    raw_signal_checks = test_raw.get("signal_checks", []) if isinstance(test_raw, dict) else []

    # When the test plan has no signal checks and no top-level pin, skip signal
    # capture entirely and return a noop step.  This is used by debug-path-only
    # tests (e.g. minimal_runtime_mailbox) whose result comes from the mailbox,
    # not from GPIO observation.
    test_pin_early = test_raw.get("pin") if isinstance(test_raw, dict) else None
    if (isinstance(raw_signal_checks, list) and len(raw_signal_checks) == 0
            and not test_pin_early
            and not is_meter_digital_verify_test(test_raw, board_cfg)):
        return {
            "name": "check_signal",
            "type": "check.noop",
            "inputs": {"note": "no signal checks — skipped (mailbox-only test)"},
        }

    signal_checks = []
    if isinstance(raw_signal_checks, list):
        for index, item in enumerate(raw_signal_checks):
            if not isinstance(item, dict):
                continue
            pin_name = item.get("pin")
            resolved_pin = pin_name
            if pin_name and isinstance(observe_map, dict) and pin_name in observe_map:
                resolved_pin = observe_map.get(pin_name)
            if not resolved_pin:
                continue
            signal_checks.append(
                {
                    "name": str(item.get("name") or f"signal_{index + 1}"),
                    "pin": str(pin_name or ""),
                    "resolved_pin": str(resolved_pin),
                    "expected_hz": float(item.get("expected_hz", 1.0)),
                    "duration_s": float(item.get("duration_s", test_raw.get("duration_s", 3.0))),
                    "min_edges": int(item.get("min_edges", test_raw.get("min_edges", 2))),
                    "max_edges": int(item.get("max_edges", test_raw.get("max_edges", 6))),
                    "min_freq_hz": item.get("min_freq_hz"),
                    "max_freq_hz": item.get("max_freq_hz"),
                    "duty_min": item.get("duty_min"),
                    "duty_max": item.get("duty_max"),
                }
            )
    test_pin = test_raw.get("pin") if isinstance(test_raw, dict) else None
    pin_value = signal_checks[0]["resolved_pin"] if signal_checks else test_pin
    if not signal_checks and test_pin and isinstance(observe_map, dict) and test_pin in observe_map:
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
            "signal_checks": signal_checks,
            "signal_relations": (list(test_raw.get("signal_relations", [])) if isinstance(test_raw, dict) and isinstance(test_raw.get("signal_relations"), list) else []),
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
                "expected_state": test_raw.get("expected_state") if isinstance(test_raw, dict) else None,
            },
            "verify_prep": (dict(board_cfg.get("verify_prep", {})) if isinstance(board_cfg, dict) and isinstance(board_cfg.get("verify_prep"), dict) else {}),
            "led_observe_cfg": (dict(test_raw.get("observe_led", {})) if isinstance(test_raw, dict) and isinstance(test_raw.get("observe_led"), dict) else {}),
            "recovery_demo": (test_raw.get("recovery_demo", {}) if isinstance(test_raw, dict) and isinstance(test_raw.get("recovery_demo"), dict) else {}),
        },
    }
    recovery_demo = step["inputs"].get("recovery_demo", {})
    if isinstance(recovery_demo, dict) and bool(recovery_demo.get("fail_first")):
        # Ensure runner reaches recovery flow immediately on first injected failure.
        step["retry_budget"] = 0
        step["rewind_anchor"] = "check_signal"
    return step


def build_mailbox_verify_step(
    test_raw: Dict[str, Any] | Any,
    probe_cfg: Dict[str, Any] | Any,
    artifacts_dir: Path,
    board_raw: Dict[str, Any] | Any = None,
) -> Dict[str, Any] | None:
    """Return a check.mailbox_verify step if the test plan declares mailbox_verify.

    The test plan may use either:
      "mailbox_verify": true               — use all defaults
      "mailbox_verify": {"settle_s": 3}    — override specific fields

    Board config may supply ``mailbox_verify_defaults`` under its ``board:``
    key.  These act as instrument-specific defaults that sit between the
    hard-coded fallbacks and the per-test-plan values, so priority is:

      hard-coded defaults < board mailbox_verify_defaults < test plan values

    This lets test plans stay instrument-agnostic: switching instruments only
    requires switching board configs (or packs), not editing every test plan.

    Returns None if no mailbox_verify config is present, so the caller can
    skip appending the step without further checks.
    """
    if not isinstance(test_raw, dict):
        return None
    mb_cfg = test_raw.get("mailbox_verify")
    if not mb_cfg:
        return None
    if mb_cfg is True:
        mb_cfg = {}
    if not isinstance(mb_cfg, dict):
        return None

    # Collect board-level mailbox_verify_defaults (instrument-specific defaults)
    board_mb_defaults: Dict[str, Any] = {}
    if isinstance(board_raw, dict):
        board_section = board_raw.get("board", {})
        if isinstance(board_section, dict):
            bd = board_section.get("mailbox_verify_defaults", {})
            if isinstance(bd, dict):
                board_mb_defaults = bd

    # Merge: board defaults first, then test plan values override
    merged = {**board_mb_defaults, **mb_cfg}

    probe = probe_cfg if isinstance(probe_cfg, dict) else {}
    probe_ip   = probe.get("ip", "")
    probe_port = int(probe.get("gdb_port", 4242))

    return {
        "name": "check_mailbox",
        "type": "check.mailbox_verify",
        "inputs": {
            "probe_ip":   probe_ip,
            "probe_port": probe_port,
            "target_id":        int(merged.get("target_id", 1)),
            "addr":             str(merged.get("addr", "0x20007F00")),
            "settle_s":         float(merged.get("settle_s", 0.0)),
            "skip_attach":      bool(merged.get("skip_attach", False)),
            "halt_before_read": bool(merged.get("halt_before_read", False)),
            "attach_monitor_cmd": str(merged.get("attach_monitor_cmd", "monitor swdp_scan")),
            "out_json":         str(artifacts_dir / "mailbox_verify.json"),
        },
    }
