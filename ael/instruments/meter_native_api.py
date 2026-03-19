from __future__ import annotations

from typing import Any, Dict, Optional

from ael.instruments import provision as instrument_provision
from ael.instruments.backends.esp32_meter.backend import Esp32MeterBackend


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


def _cfg_from_manifest(manifest: Dict[str, Any], *, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    communication = manifest.get("communication", {}) if isinstance(manifest.get("communication"), dict) else {}
    endpoint = str(communication.get("endpoint") or "").strip()
    default_host = "192.168.4.1"
    default_port = 9000
    if endpoint and ":" in endpoint:
        h, p = endpoint.rsplit(":", 1)
        default_host = h or default_host
        try:
            default_port = int(p)
        except Exception:
            default_port = 9000
    return {
        "host": str(host or default_host),
        "port": int(port or default_port),
    }


def _backend_from_manifest(
    manifest: Dict[str, Any],
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    timeout_s: float = 3.0,
) -> Esp32MeterBackend:
    cfg = _cfg_from_manifest(manifest, host=host, port=port)
    return Esp32MeterBackend(
        host=cfg["host"],
        port=cfg["port"],
        timeout_s=timeout_s,
    )


def _execute_action(
    manifest: Dict[str, Any],
    action: str,
    params: Dict[str, Any],
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    unwrap_raw: bool = False,
) -> Dict[str, Any]:
    result = _backend_from_manifest(manifest, host=host, port=port).execute(action, params)
    if result.get("status") == "success":
        data = (result.get("data") or {}) if isinstance(result.get("data"), dict) else {}
        if unwrap_raw and isinstance(data.get("raw"), dict):
            return _native_ok(data["raw"])
        return _native_ok(data)
    error = (result.get("error") or {}) if isinstance(result.get("error"), dict) else {}
    return _native_error(
        str(error.get("code") or f"{action}_failed"),
        str(error.get("message") or f"{action} failed"),
        retryable=True,
        details={"action": action},
    )


def native_interface_profile() -> Dict[str, Any]:
    return {
        "name": "Local Instrument Interface",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_native_api",
        "metadata_commands": ["identify", "get_capabilities", "get_status", "doctor"],
        "action_commands": ["measure_digital", "measure_voltage", "stim_digital"],
        "response_model": {
            "success": {"status": "ok", "data": "..."},
            "error": {
                "status": "error",
                "error": {"code": "string", "message": "string", "retryable": False},
            },
        },
    }


def identify(manifest: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest)
    return _native_ok(
        {
            "device_id": str(manifest.get("id") or "meter"),
            "device_type": "meter",
            "model": str(manifest.get("model") or "ESP32 Meter"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": f"{cfg['host']}:{cfg['port']}",
            "communication_protocol": ((manifest.get("communication") or {}) if isinstance(manifest.get("communication"), dict) else {}).get("protocol"),
        }
    )


def get_capabilities(manifest: Dict[str, Any]) -> Dict[str, Any]:
    caps: Dict[str, Any] = {}
    for item in manifest.get("capabilities") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        caps[name] = {
            "version": item.get("version"),
            "channels": item.get("channels"),
            "params": item.get("params"),
            "limits": item.get("limits"),
        }
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "capabilities": caps,
        }
    )


def get_status(manifest: Dict[str, Any], *, host: Optional[str] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host)
    try:
        payload = instrument_provision.ensure_meter_reachable(manifest=manifest, host=cfg["host"], timeout_s=timeout_s)
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "host": cfg["host"],
                "port": cfg["port"],
                "reachability": payload,
            }
        )
    except Exception as exc:
        return _native_error(
            "meter_status_failed",
            str(exc),
            retryable=True,
            details={"host": cfg["host"], "port": cfg["port"], "protocol_version": NATIVE_API_PROTOCOL},
        )


def doctor(manifest: Dict[str, Any], *, host: Optional[str] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host)
    try:
        payload = instrument_provision.ensure_meter_reachable(manifest=manifest, host=cfg["host"], timeout_s=timeout_s)
        return _native_ok(payload)
    except Exception as exc:
        return _native_error(
            "meter_doctor_failed",
            str(exc),
            retryable=True,
            details={"host": cfg["host"], "port": cfg["port"], "protocol_version": NATIVE_API_PROTOCOL},
        )


def measure_digital(manifest: Dict[str, Any], *, pins: list[int], duration_ms: int = 500, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    return _execute_action(
        manifest,
        "gpio_measure",
        {"channels": list(pins), "duration_ms": int(duration_ms)},
        host=host,
        port=port,
        unwrap_raw=True,
    )


def measure_voltage(manifest: Dict[str, Any], *, gpio: int = 4, avg: int = 16, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    return _execute_action(
        manifest,
        "voltage_read",
        {"gpio": int(gpio), "avg": int(avg)},
        host=host,
        port=port,
        unwrap_raw=True,
    )


def stim_digital(
    manifest: Dict[str, Any],
    *,
    gpio: int,
    mode: str,
    duration_us: Optional[int] = None,
    freq_hz: Optional[int] = None,
    pattern: Optional[str] = None,
    keep: int = 0,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    return _execute_action(
        manifest,
        "stim_digital",
        {
            "gpio": int(gpio),
            "mode": mode,
            "duration_us": duration_us,
            "freq_hz": freq_hz,
            "pattern": pattern,
            "keep": int(keep),
        },
        host=host,
        port=port,
        unwrap_raw=True,
    )
