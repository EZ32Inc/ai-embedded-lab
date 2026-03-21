from __future__ import annotations

from typing import Any, Dict, Optional

from ael.instruments import provision as instrument_provision
from ael.instruments.backends.esp32_meter.backend import Esp32MeterBackend
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


NATIVE_API_PROTOCOL = "ael.local_instrument.native_api.v0.1"


# ── Capabilities ──────────────────────────────────────────────────────────────

METER_CAPABILITIES = {
    "measure.digital": {"actions": ["measure_digital"], "surfaces": ["meter_tcp"]},
    "measure.voltage": {"actions": ["measure_voltage"], "surfaces": ["meter_tcp"]},
    "stim.digital": {"actions": ["stim_digital"], "surfaces": ["meter_tcp"]},
}


# ── Fallbacks ─────────────────────────────────────────────────────────────────

STATUS_FALLBACK = {
    "strategy": "recover_meter_connectivity",
    "suggestion": "confirm the ESP32 meter is reachable on its control endpoint before measuring or stimulating",
}

DOCTOR_FALLBACK = {
    "strategy": "recover_meter_then_retry",
    "suggestion": "restore ESP32 meter reachability or power before retrying measurement work",
}

MEASURE_DIGITAL_FALLBACK = {
    "strategy": "recover_meter_then_retry_measurement",
    "suggestion": "restore ESP32 meter connectivity before retrying digital measurement",
}

MEASURE_VOLTAGE_FALLBACK = {
    "strategy": "recover_meter_then_retry_measurement",
    "suggestion": "restore ESP32 meter connectivity before retrying voltage measurement",
}

STIM_DIGITAL_FALLBACK = {
    "strategy": "recover_meter_then_retry_stimulus",
    "suggestion": "restore ESP32 meter connectivity before retrying digital stimulation",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _native_ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "ok", "data": data}


def _native_error(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
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
        str(error.get("code") or "action_failed"),
        str(error.get("message") or f"{action} failed"),
        retryable=True,
        details={"action": action},
    )


# ── Public profile / identity (passed to InstrumentProvider) ──────────────────

def native_interface_profile() -> Dict[str, Any]:
    return {
        "name": "ESP32 Meter Native Instrument Interface",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_native_api",
        "instrument_family": "esp32_meter",
        "instrument_identity": "measurement_and_stimulus_instrument",
        "metadata_commands": ["identify", "get_capabilities", "get_status", "doctor"],
        "action_commands": ["measure_digital", "measure_voltage", "stim_digital"],
        "status_domains": [
            "network",
            "meter_service",
            "measurement_surface",
            "stimulation_surface",
        ],
        "lifecycle_scope": {
            "owned_by_native_api": [
                "identify",
                "get_capabilities",
                "get_status",
                "doctor",
                "measure_digital",
                "measure_voltage",
                "stim_digital",
            ],
            "owned_by_backend": [
                "gpio_measure",
                "voltage_read",
                "stim_digital",
            ],
            "out_of_scope": [
                "provision",
                "wifi_onboarding",
                "firmware_update",
            ],
        },
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
            "device_type": "measurement_and_stimulus_instrument",
            "instrument_family": "esp32_meter",
            "instrument_role": "external_instrument",
            "model": str(manifest.get("model") or "ESP32 Meter"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": f"{cfg['host']}:{cfg['port']}",
            "communication_protocol": ((manifest.get("communication") or {}) if isinstance(manifest.get("communication"), dict) else {}).get("protocol"),
        }
    )


# ── Private native implementations ────────────────────────────────────────────

def _meter_get_capabilities(manifest: Dict[str, Any]) -> Dict[str, Any]:
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
            "instrument_family": "esp32_meter",
            "capability_families": {
                "digital_measurement": {
                    "actions": ["measure_digital"],
                    "surface": "meter_tcp",
                },
                "voltage_measurement": {
                    "actions": ["measure_voltage"],
                    "surface": "meter_tcp",
                },
                "digital_stimulation": {
                    "actions": ["stim_digital"],
                    "surface": "meter_tcp",
                },
            },
            "capabilities": caps,
        }
    )


def _meter_get_status(manifest: Dict[str, Any], *, host: Optional[str] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host)
    try:
        payload = instrument_provision.ensure_meter_reachable(manifest=manifest, host=cfg["host"], timeout_s=timeout_s)
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "instrument_family": "esp32_meter",
                "host": cfg["host"],
                "port": cfg["port"],
                "reachability": payload,
                "health_domains": {
                    "network": {"ok": bool(payload.get("ok"))},
                    "meter_service": {"ok": bool(payload.get("ok"))},
                    "measurement_surface": {"ok": bool(payload.get("ok"))},
                    "stimulation_surface": {"ok": bool(payload.get("ok"))},
                },
            }
        )
    except Exception as exc:
        return _native_error(
            "backend_error",
            str(exc),
            retryable=True,
            details={"host": cfg["host"], "port": cfg["port"], "protocol_version": NATIVE_API_PROTOCOL},
        )


def _meter_doctor(manifest: Dict[str, Any], *, host: Optional[str] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    cfg = _cfg_from_manifest(manifest, host=host)
    try:
        payload = instrument_provision.ensure_meter_reachable(manifest=manifest, host=cfg["host"], timeout_s=timeout_s)
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "instrument_family": "esp32_meter",
                "reachable": bool(payload.get("ok")),
                "checks": {
                    "network": {"ok": bool(payload.get("ok"))},
                    "meter_service": {"ok": bool(payload.get("ok"))},
                    "measurement_surface": {"ok": bool(payload.get("ok"))},
                    "stimulation_surface": {"ok": bool(payload.get("ok"))},
                    "reachability": payload,
                },
                "lifecycle_boundary": native_interface_profile().get("lifecycle_scope"),
            }
        )
    except Exception as exc:
        return _native_error(
            "doctor_failed",
            str(exc),
            retryable=True,
            details={"host": cfg["host"], "port": cfg["port"], "protocol_version": NATIVE_API_PROTOCOL},
        )


def _meter_measure_digital(
    manifest: Dict[str, Any],
    *,
    pins: list[int],
    duration_ms: int = 500,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    return _execute_action(
        manifest,
        "gpio_measure",
        {"channels": list(pins), "duration_ms": int(duration_ms)},
        host=host,
        port=port,
        unwrap_raw=True,
    )


def _meter_measure_voltage(
    manifest: Dict[str, Any],
    *,
    gpio: int = 4,
    avg: int = 16,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    return _execute_action(
        manifest,
        "voltage_read",
        {"gpio": int(gpio), "avg": int(avg)},
        host=host,
        port=port,
        unwrap_raw=True,
    )


def _meter_stim_digital(
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


# ── Interface layer ───────────────────────────────────────────────────────────

def _get_capabilities(manifest):
    payload = _meter_get_capabilities(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="esp32_meter",
            capabilities=METER_CAPABILITIES,
            lifecycle_boundary=native_interface_profile().get("lifecycle_scope"),
        ),
        failure_boundary="instrument_capabilities",
    )


def _get_status(manifest):
    payload = _meter_get_status(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="get_status",
        success_mapper=lambda data: normalize_status_result(
            family="esp32_meter",
            reachable=(data.get("reachability") or {}).get("ok") if isinstance(data.get("reachability"), dict) else None,
            health_domains=(data.get("health_domains") or {}) if isinstance(data.get("health_domains"), dict) else {},
            endpoints={"meter_tcp": f"{data.get('host')}:{data.get('port')}"} if data.get("host") and data.get("port") is not None else {},
            observations={"reachability": data.get("reachability")} if isinstance(data.get("reachability"), dict) else {},
        ),
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )


def _doctor(manifest):
    payload = _meter_doctor(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="doctor",
        success_mapper=lambda data: normalize_doctor_result(
            family="esp32_meter",
            reachable=data.get("reachable"),
            checks=(data.get("checks") or {}) if isinstance(data.get("checks"), dict) else {},
            lifecycle_boundary=data.get("lifecycle_boundary") if isinstance(data.get("lifecycle_boundary"), dict) else None,
            recovery_hint="restore ESP32 meter reachability or power before retrying measurement work",
            failure_boundary="probe_health",
        ),
        failure_boundary="probe_health",
        fallback=DOCTOR_FALLBACK,
    )


def _measure_digital(manifest, **kwargs):
    requested = {
        "pins": list(kwargs.get("pins") or []),
        "duration_ms": kwargs.get("duration_ms", 500),
    }
    payload = _meter_measure_digital(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="measure_digital",
        requested=requested,
        success_mapper=lambda data: {
            "measurement_kind": "digital",
            "pins": list(data.get("pins") or []),
            "duration_ms": data.get("duration_ms", kwargs.get("duration_ms", 500)),
            "sample_count": data.get("samples"),
            "result_rows": list(data.get("pins") or []),
        },
        failure_boundary="measurement",
        fallback=MEASURE_DIGITAL_FALLBACK,
    )


def _measure_voltage(manifest, **kwargs):
    requested = {
        "gpio": kwargs.get("gpio", 4),
        "avg": kwargs.get("avg", 16),
    }
    payload = _meter_measure_voltage(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="measure_voltage",
        requested=requested,
        success_mapper=lambda data: {
            "measurement_kind": "voltage",
            "gpio": data.get("gpio", kwargs.get("gpio", 4)),
            "avg": data.get("avg", kwargs.get("avg", 16)),
            "voltage_v": data.get("voltage_v", data.get("v", data.get("value_v", data.get("voltage", data.get("value"))))),
            "v": data.get("v", data.get("voltage_v", data.get("value_v", data.get("voltage", data.get("value"))))),
            "mv": data.get("mv"),
            "result": dict(data),
        },
        failure_boundary="measurement",
        fallback=MEASURE_VOLTAGE_FALLBACK,
    )


def _stim_digital(manifest, **kwargs):
    requested = {
        "gpio": kwargs["gpio"],
        "mode": kwargs["mode"],
        "duration_us": kwargs.get("duration_us"),
        "freq_hz": kwargs.get("freq_hz"),
        "pattern": kwargs.get("pattern"),
        "keep": kwargs.get("keep", 0),
    }
    payload = _meter_stim_digital(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="stim_digital",
        requested=requested,
        success_mapper=lambda data: {
            "stimulus_kind": "digital",
            "gpio": data.get("gpio", kwargs["gpio"]),
            "mode": data.get("mode", kwargs["mode"]),
            "duration_us": data.get("duration_us", kwargs.get("duration_us")),
            "freq_hz": data.get("freq_hz", kwargs.get("freq_hz")),
            "pattern": data.get("pattern", kwargs.get("pattern")),
            "keep": data.get("keep", kwargs.get("keep", 0)),
            "result": dict(data),
        },
        failure_boundary="stimulus",
        fallback=STIM_DIGITAL_FALLBACK,
    )


PROVIDER = InstrumentProvider(
    family="esp32_meter",
    native_interface_profile=native_interface_profile,
    identify=identify,
    get_capabilities=_get_capabilities,
    get_status=_get_status,
    doctor=_doctor,
    actions={
        "measure_digital": _measure_digital,
        "measure_voltage": _measure_voltage,
        "stim_digital": _stim_digital,
    },
)
