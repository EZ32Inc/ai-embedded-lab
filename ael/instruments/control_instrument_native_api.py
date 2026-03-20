from __future__ import annotations

import json
from pathlib import Path
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


def _flash_failure_details(flash_json_path: Optional[str]) -> Dict[str, Any]:
    path = str(flash_json_path or "").strip()
    if not path:
        return {"retryable": True, "message": "control instrument firmware load failed", "details": {}}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {"retryable": True, "message": "control instrument firmware load failed", "details": {}}
    error_summary = str(payload.get("error_summary") or "").strip()
    details = {}
    if error_summary:
        details["flash_error_summary"] = error_summary
    retryable = True
    low = error_summary.lower()
    if "local st-link gdb server" in low or "st-link usb is busy" in low or "st-link usb timed out" in low or "no st-link device detected" in low or "multiple st-link devices detected" in low:
        retryable = False
    message = error_summary or "control instrument firmware load failed"
    return {"retryable": retryable, "message": message, "details": details}


def native_interface_profile() -> Dict[str, Any]:
    return {
        "name": "Legacy Control Instrument Backend",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_backend_legacy",
        "legacy_backend": True,
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
            "legacy_backend": True,
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


def _flash_success_details(flash_json_path: Optional[str]) -> Dict[str, Any]:
    path = str(flash_json_path or "").strip()
    if not path:
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, Any] = {}
    managed = payload.get("managed_stlink_server")
    if isinstance(managed, dict) and managed.get("managed") and int(managed.get("pid") or 0) > 0:
        out["managed_stlink_server"] = {
            "managed": True,
            "pid": int(managed.get("pid") or 0),
        }
    return out


def program_firmware(
    probe_cfg: Dict[str, Any],
    *,
    firmware_path: str,
    flash_cfg: Optional[Dict[str, Any]] = None,
    flash_json_path: Optional[str] = None,
) -> Dict[str, Any]:
    ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path, flash_cfg=flash_cfg or {}, flash_json_path=flash_json_path)
    if ok:
        data = {"firmware_path": firmware_path}
        data.update(_flash_success_details(flash_json_path))
        return _native_ok(data)
    failure = _flash_failure_details(flash_json_path)
    details = {"firmware_path": firmware_path, **failure.get("details", {})}
    return _native_error(
        "control_program_failed",
        str(failure.get("message") or "control instrument firmware load failed"),
        retryable=bool(failure.get("retryable", True)),
        details=details,
    )


def capture_signature(
    probe_cfg: Dict[str, Any],
    *,
    pin: str,
    pins: list[str] | None = None,
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
            pins=pins,
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
