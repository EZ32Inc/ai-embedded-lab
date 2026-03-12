from __future__ import annotations

from typing import Any, Dict, Optional

from ael.adapters import flash_bmda_gdbmi
from ael.adapters import observe_gpio_pin
from ael.adapters import preflight as preflight_adapter


NATIVE_API_PROTOCOL = "ael.local_instrument.native_api.v0.1"


def _native_ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "ok", "data": data}


def _native_error(code: str, message: str, *, retryable: bool = False, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "retryable": bool(retryable),
        },
    }
    if details:
        payload["error"]["details"] = details
    return payload


def native_interface_profile() -> Dict[str, Any]:
    return {
        "name": "Local Instrument Interface",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_native_api",
        "metadata_commands": ["identify", "get_capabilities", "get_status", "doctor"],
        "action_commands": ["preflight_probe", "program_firmware", "capture_signature", "observe_gpio"],
        "response_model": {
            "success": {"status": "ok", "data": "..."},
            "error": {
                "status": "error",
                "error": {"code": "string", "message": "string", "retryable": False},
            },
        },
    }


def identify(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return _native_ok(
        {
            "device_type": "control_instrument",
            "model": str(probe_cfg.get("name") or "ESP32JTAG"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": f"{probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}",
            "transport_protocol": str(probe_cfg.get("web_api_protocol") or probe_cfg.get("protocol") or "esp32jtag_web_api_v1"),
        }
    )


def get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "capabilities": {
                "observe.gpio": {"pins": "P0.x / PAx style verify lines"},
                "capture.signature": {"pins": "single verify pin for signal capture"},
            },
        }
    )


def get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": f"{probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}",
            "present": True,
        }
    )


def doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    if ok:
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "endpoint": f"{probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}",
                "reachable": True,
                "preflight": info,
            }
        )
    return _native_error(
        "control_doctor_failed",
        "control instrument doctor failed",
        retryable=True,
        details={
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": f"{probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}",
            "preflight": info,
        },
    )


def preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    if ok:
        return _native_ok(info or {})
    return _native_error("control_preflight_failed", "control instrument preflight failed", retryable=True, details={"preflight": info or {}})


def program_firmware(
    probe_cfg: Dict[str, Any],
    *,
    firmware_path: str,
    flash_cfg: Optional[Dict[str, Any]] = None,
    flash_json_path: Optional[str] = None,
) -> Dict[str, Any]:
    ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path, flash_cfg=flash_cfg or {}, flash_json_path=flash_json_path)
    if ok:
        return _native_ok({"firmware_path": firmware_path})
    return _native_error(
        "control_program_failed",
        "control instrument firmware load failed",
        retryable=True,
        details={"firmware_path": firmware_path},
    )


def capture_signature(
    probe_cfg: Dict[str, Any],
    *,
    pin: str,
    duration_s: float,
    expected_hz: float,
    min_edges: int,
    max_edges: int,
) -> Dict[str, Any]:
    capture: Dict[str, Any] = {}
    try:
        ok = observe_gpio_pin.run(
            probe_cfg,
            pin=pin,
            duration_s=duration_s,
            expected_hz=expected_hz,
            min_edges=min_edges,
            max_edges=max_edges,
            capture_out=capture,
            verify_edges=False,
        )
    except Exception as exc:
        return _native_error("capture_signature_failed", str(exc), retryable=True)
    if not ok:
        return _native_error("capture_signature_failed", "gpio capture failed", retryable=True, details={"capture": capture})
    return _native_ok(capture)


def observe_gpio(
    probe_cfg: Dict[str, Any],
    *,
    pin: str,
    duration_s: float,
    expected_hz: float,
    min_edges: int,
    max_edges: int,
) -> Dict[str, Any]:
    return capture_signature(
        probe_cfg,
        pin=pin,
        duration_s=duration_s,
        expected_hz=expected_hz,
        min_edges=min_edges,
        max_edges=max_edges,
    )
