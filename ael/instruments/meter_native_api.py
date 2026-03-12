from __future__ import annotations

from typing import Any, Dict, Optional

from ael.adapters import esp32s3_dev_c_meter_tcp
from ael.instruments import provision as instrument_provision


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


def identify(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return _native_ok(
        {
            "device_type": str(manifest.get("id") or "meter"),
            "model": str(manifest.get("model") or "ESP32 Meter"),
            "protocol_version": NATIVE_API_PROTOCOL,
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
        return _native_error("meter_status_failed", str(exc), retryable=True)


def doctor(manifest: Dict[str, Any], *, host: Optional[str] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host)
    try:
        payload = instrument_provision.ensure_meter_reachable(manifest=manifest, host=cfg["host"], timeout_s=timeout_s)
        return _native_ok(payload)
    except Exception as exc:
        return _native_error("meter_doctor_failed", str(exc), retryable=True)


def measure_digital(manifest: Dict[str, Any], *, pins: list[int], duration_ms: int = 500, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host, port=port)
    try:
        payload = esp32s3_dev_c_meter_tcp.measure_digital(cfg, pins=pins, duration_ms=duration_ms)
        return _native_ok(payload)
    except Exception as exc:
        return _native_error("measure_digital_failed", str(exc), retryable=True)


def measure_voltage(manifest: Dict[str, Any], *, gpio: int = 4, avg: int = 16, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host, port=port)
    try:
        payload = esp32s3_dev_c_meter_tcp.measure_voltage(cfg, gpio=gpio, avg=avg)
        return _native_ok(payload)
    except Exception as exc:
        return _native_error("measure_voltage_failed", str(exc), retryable=True)


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
    cfg = _cfg_from_manifest(manifest, host=host, port=port)
    try:
        payload = esp32s3_dev_c_meter_tcp.stim_digital(
            cfg,
            gpio=gpio,
            mode=mode,
            duration_us=duration_us,
            freq_hz=freq_hz,
            pattern=pattern,
            keep=keep,
        )
        return _native_ok(payload)
    except Exception as exc:
        return _native_error("stim_digital_failed", str(exc), retryable=True)
