from __future__ import annotations

import socket
from typing import Any, Dict, Optional

from ael.adapters import preflight as preflight_adapter
from ael.instruments import controller_backend
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


NATIVE_API_PROTOCOL = "ael.local_instrument.jtag_native_api.v0.1"


# ── Capabilities ──────────────────────────────────────────────────────────────

JTAG_CAPABILITIES = {
    "probe.preflight": {"actions": ["preflight_probe"], "surfaces": ["instrument_native_api"]},
    "debug.flash": {"actions": ["program_firmware"], "surfaces": ["gdb_remote"]},
    "debug.reset": {"actions": ["reset"], "surfaces": ["reset_out"]},
    "debug.halt": {"actions": ["debug_halt"], "surfaces": ["gdb_remote"]},
    "debug.memory_read": {"actions": ["debug_read_memory"], "surfaces": ["gdb_remote"]},
    "capture.digital": {"actions": ["capture_signature"], "surfaces": ["web_api"]},
}


# ── Fallbacks ─────────────────────────────────────────────────────────────────

STATUS_FALLBACK = {
    "strategy": "refresh_probe_status",
    "suggestion": "re-check ESP32 JTAG connectivity and rerun preflight before using the setup",
}

DOCTOR_FALLBACK = {
    "strategy": "rerun_preflight_then_retry",
    "suggestion": "rerun ESP32 JTAG preflight and inspect monitor targets plus logic-analyzer self-test before retrying",
}

PROGRAM_FIRMWARE_FALLBACK = {
    "strategy": "retry_same_setup",
    "suggestion": "retry firmware programming on the same ESP32 JTAG setup after re-running preflight",
}

CAPTURE_SIGNATURE_FALLBACK = {
    "strategy": "rerun_capture_after_preflight",
    "suggestion": "rerun preflight and verify capture wiring before retrying signature capture on the ESP32 JTAG setup",
}

PREFLIGHT_FALLBACK = {
    "strategy": "rerun_preflight_then_retry",
    "suggestion": "rerun ESP32 JTAG preflight and inspect monitor targets before retrying",
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


def _endpoint_map(probe_cfg: Dict[str, Any]) -> Dict[str, str]:
    communication = probe_cfg.get("communication", {}) if isinstance(probe_cfg.get("communication"), dict) else {}
    surfaces = communication.get("surfaces") if isinstance(communication.get("surfaces"), list) else []
    endpoints: Dict[str, str] = {}
    for item in surfaces:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        endpoint = str(item.get("endpoint") or "").strip()
        if name and endpoint:
            endpoints[name] = endpoint
    ip = str(probe_cfg.get("ip") or "").strip()
    gdb_port = probe_cfg.get("gdb_port")
    if "debug_remote" not in endpoints and ip and gdb_port is not None:
        endpoints["debug_remote"] = f"{ip}:{gdb_port}"
    return endpoints


def _split_host_port(text: str | None) -> tuple[str | None, int | None]:
    raw = str(text or "").strip()
    if not raw:
        return None, None
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0]
    if ":" not in raw:
        return raw or None, None
    host, port = raw.rsplit(":", 1)
    try:
        return host.strip() or None, int(port)
    except Exception:
        return host.strip() or None, None


def _tcp_check(endpoint: str | None, timeout_s: float = 1.0) -> Dict[str, Any]:
    host, port = _split_host_port(endpoint)
    if not host or port is None:
        return {"ok": False, "error": "missing host/port", "endpoint": endpoint}
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return {"ok": True, "host": host, "port": int(port), "endpoint": endpoint}
    except Exception as exc:
        return {"ok": False, "host": host, "port": int(port), "endpoint": endpoint, "error": str(exc)}


# ── Public profile / identity (passed to InstrumentProvider) ──────────────────

def native_interface_profile() -> Dict[str, Any]:
    return {
        "name": "ESP32JTAG Native Instrument Interface",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_native_api",
        "instrument_family": "esp32jtag",
        "instrument_identity": "multi_capability_instrument",
        "metadata_commands": ["identify", "get_capabilities", "get_status", "doctor"],
        "action_commands": ["preflight_probe", "program_firmware", "capture_signature"],
        "status_domains": [
            "network",
            "gdb_remote",
            "web_api",
            "capture_subsystem",
            "monitor_targets",
        ],
        "lifecycle_scope": {
            "owned_by_native_api": ["identify", "get_capabilities", "get_status", "doctor", "preflight_probe", "program_firmware", "capture_signature"],
            "owned_by_backend": ["flash", "reset", "debug_halt", "debug_read_memory", "gpio_measure"],
            "out_of_scope": ["provision", "service_restart", "firmware_update"],
        },
        "response_model": {
            "success": {"status": "ok", "data": "..."},
            "error": {
                "status": "error",
                "error": {"code": "string", "message": "string", "retryable": False},
            },
        },
    }


def identify(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    endpoints = _endpoint_map(probe_cfg)
    return _native_ok(
        {
            "device_id": str(probe_cfg.get("instance_id") or probe_cfg.get("name") or "esp32jtag"),
            "device_type": "multi_capability_instrument",
            "instrument_family": "esp32jtag",
            "instrument_role": "control",
            "model": str(probe_cfg.get("name") or "ESP32JTAG"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "communication_endpoints": endpoints,
            "capability_families": ["debug_remote", "capture_control", "reset_control", "preflight"],
        }
    )


# ── Private native implementations ────────────────────────────────────────────

def _jtag_get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    capability_surfaces = probe_cfg.get("capability_surfaces", {}) if isinstance(probe_cfg.get("capability_surfaces"), dict) else {}
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "capability_families": {
                "debug_remote": {
                    "actions": ["flash", "debug_halt", "debug_read_memory"],
                    "surface": capability_surfaces.get("swd", "gdb_remote"),
                    "owned_by": "esp32_jtag_backend",
                },
                "reset_control": {
                    "actions": ["reset"],
                    "surface": capability_surfaces.get("reset_out"),
                    "owned_by": "esp32_jtag_backend",
                },
                "capture_control": {
                    "actions": ["gpio_measure"],
                    "surface": capability_surfaces.get("gpio_in", "web_api"),
                    "owned_by": "esp32_jtag_backend",
                },
                "preflight": {
                    "actions": ["preflight_probe"],
                    "surface": "instrument_native_api",
                    "owned_by": "esp32jtag",
                },
                "firmware_programming": {
                    "actions": ["program_firmware"],
                    "surface": capability_surfaces.get("swd", "gdb_remote"),
                    "owned_by": "esp32jtag",
                },
                "capture_signature": {
                    "actions": ["capture_signature"],
                    "surface": capability_surfaces.get("gpio_in", "web_api"),
                    "owned_by": "esp32jtag",
                },
            },
        }
    )


def _jtag_get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    endpoints = _endpoint_map(probe_cfg)
    debug_remote = endpoints.get("debug_remote")
    control_api = endpoints.get("web_api")
    debug_check = _tcp_check(debug_remote)
    control_check = _tcp_check(control_api) if control_api else {"ok": False, "error": "missing endpoint", "endpoint": control_api}
    network_ok = bool(debug_check.get("ok") or control_check.get("ok"))
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "reachable": network_ok,
            "endpoints": {
                "debug_remote": debug_check,
                "control_api": control_check,
            },
            "health_domains": {
                "network": {
                    "ok": network_ok,
                    "summary": "at least one ESP32JTAG service endpoint is reachable" if network_ok else "no ESP32JTAG service endpoints are reachable",
                },
                "debug_remote": {"ok": bool(debug_check.get("ok"))},
                "web_api": {"ok": bool(control_check.get("ok"))},
                "capture": {
                    "ok": bool(control_check.get("ok")),
                    "dependency": "web_api",
                },
                "logic_analyzer": {
                    "ok": None,
                    "state": "unverified",
                    "detail": "monitor target enumeration runs during doctor/preflight",
                },
            },
        }
    )


def _jtag_doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    status = _jtag_get_status(probe_cfg)
    if status.get("status") != "ok":
        return _native_error("doctor_failed", "jtag doctor failed to collect status", retryable=True)
    status_data = (status.get("data") or {}) if isinstance(status.get("data"), dict) else {}
    health_domains = (status_data.get("health_domains") or {}) if isinstance(status_data.get("health_domains"), dict) else {}
    preflight_info = info or {}
    monitor_targets = preflight_info.get("targets") or []
    monitor_ok = bool(preflight_info.get("monitor_ok"))
    la_ok = bool(preflight_info.get("la_ok") or preflight_info.get("logic_analyzer"))
    payload = {
        "protocol_version": NATIVE_API_PROTOCOL,
        "reachable": bool(ok),
        "checks": {
            "network": {"ok": bool((health_domains.get("network") or {}).get("ok"))},
            "gdb_remote": {"ok": bool((health_domains.get("debug_remote") or {}).get("ok"))},
            "web_api": {"ok": bool((health_domains.get("web_api") or {}).get("ok"))},
            "capture_control": {
                "ok": la_ok,
                "detail": "logic-analyzer self-test passed" if la_ok else "logic-analyzer self-test failed",
            },
            "logic_analyzer": {
                "ok": monitor_ok,
                "targets": monitor_targets,
            },
            "preflight": {"ok": bool(ok), "detail": preflight_info},
        },
        "lifecycle_boundary": native_interface_profile().get("lifecycle_scope"),
    }
    if ok:
        return _native_ok(payload)
    return _native_error("doctor_failed", "jtag instrument doctor failed", retryable=True, details=payload)


def _jtag_preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    if ok:
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "preflight": info or {},
            }
        )
    return _native_error(
        "preflight_failed",
        "jtag instrument preflight failed",
        retryable=True,
        details={
            "protocol_version": NATIVE_API_PROTOCOL,
            "preflight": info or {},
        },
    )


# ── Capability map for interface layer ────────────────────────────────────────

def _capability_map(probe_cfg):
    capability_surfaces = probe_cfg.get("capability_surfaces", {}) if isinstance(probe_cfg.get("capability_surfaces"), dict) else {}
    mapping = {key: {**value} for key, value in JTAG_CAPABILITIES.items()}
    mapping["debug.flash"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.halt"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.memory_read"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.reset"]["surfaces"] = [str(capability_surfaces.get("reset_out") or "reset_out")]
    mapping["capture.digital"]["surfaces"] = [str(capability_surfaces.get("gpio_in") or "web_api")]
    return mapping


# ── Interface layer ───────────────────────────────────────────────────────────

def _preflight_probe(probe_cfg):
    payload = _jtag_preflight_probe(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="preflight_probe",
        success_mapper=lambda data: {
            "transport": "gdb_remote",
            "targets": list((data.get("preflight") or {}).get("targets") or []),
            "monitor_ok": bool((data.get("preflight") or {}).get("monitor_ok")),
            "logic_analyzer_ok": bool(
                (data.get("preflight") or {}).get("la_ok")
                or (data.get("preflight") or {}).get("logic_analyzer")
            ),
            "preflight": data.get("preflight") if isinstance(data.get("preflight"), dict) else {},
        },
        failure_boundary="probe_health",
        fallback=PREFLIGHT_FALLBACK,
    )


def _get_capabilities(probe_cfg):
    payload = _jtag_get_capabilities(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="esp32jtag",
            capabilities=_capability_map(probe_cfg),
            lifecycle_boundary=native_interface_profile().get("lifecycle_scope"),
        ),
        failure_boundary="instrument_capabilities",
    )


def _get_status(probe_cfg):
    payload = _jtag_get_status(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="get_status",
        success_mapper=lambda data: normalize_status_result(
            family="esp32jtag",
            reachable=data.get("reachable"),
            health_domains=(data.get("health_domains") or {}) if isinstance(data.get("health_domains"), dict) else {},
            endpoints=(data.get("endpoints") or {}) if isinstance(data.get("endpoints"), dict) else {},
        ),
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )


def _doctor(probe_cfg):
    payload = _jtag_doctor(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="doctor",
        success_mapper=lambda data: normalize_doctor_result(
            family="esp32jtag",
            reachable=data.get("reachable"),
            checks=(data.get("checks") or {}) if isinstance(data.get("checks"), dict) else {},
            lifecycle_boundary=data.get("lifecycle_boundary") if isinstance(data.get("lifecycle_boundary"), dict) else None,
            recovery_hint="rerun preflight and inspect monitor targets plus logic-analyzer self-test",
            failure_boundary="probe_health",
        ),
        failure_boundary="probe_health",
        fallback=DOCTOR_FALLBACK,
    )


def _program_firmware(probe_cfg, **kwargs):
    requested = {
        "firmware_path": kwargs.get("firmware_path"),
        "transport": "gdb_remote",
    }
    payload = controller_backend.program_firmware(probe_cfg, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="program_firmware",
        requested=requested,
        success_mapper=lambda data: {
            "firmware_path": data.get("firmware_path"),
            "transport": "gdb_remote",
            "managed_debug_server": data.get("managed_stlink_server"),
        },
        failure_boundary="firmware_programming",
        fallback=PROGRAM_FIRMWARE_FALLBACK,
    )


def _capture_signature(probe_cfg, **kwargs):
    requested = {
        "pin": kwargs.get("pin"),
        "pins": list(kwargs.get("pins") or []),
        "duration_s": kwargs.get("duration_s"),
        "expected_hz": kwargs.get("expected_hz"),
        "min_edges": kwargs.get("min_edges"),
        "max_edges": kwargs.get("max_edges"),
    }
    payload = controller_backend.capture_signature(probe_cfg, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="capture_signature",
        requested=requested,
        success_mapper=lambda data: {
            "pin": data.get("pin") or kwargs.get("pin"),
            "pins": list(kwargs.get("pins") or ([data.get("pin")] if data.get("pin") else [kwargs.get("pin")]) or []),
            "duration_s": kwargs.get("duration_s"),
            "expected_hz": kwargs.get("expected_hz"),
            "edge_count": data.get("edges"),
            "high_count": data.get("high"),
            "low_count": data.get("low"),
            "capture_blob_present": data.get("blob") is not None,
            "blob": data.get("blob"),
            "sample_rate_hz": data.get("sample_rate_hz"),
            "bit": data.get("bit"),
            "pin_bits": data.get("pin_bits") if isinstance(data.get("pin_bits"), dict) else {},
            "targetin_result": dict(data.get("targetin_result") or {}) if isinstance(data.get("targetin_result"), dict) else None,
        },
        failure_boundary="signal_capture",
        fallback=CAPTURE_SIGNATURE_FALLBACK,
    )


PROVIDER = InstrumentProvider(
    family="esp32jtag",
    native_interface_profile=native_interface_profile,
    identify=identify,
    get_capabilities=_get_capabilities,
    get_status=_get_status,
    doctor=_doctor,
    actions={
        "preflight_probe": _preflight_probe,
        "program_firmware": _program_firmware,
        "capture_signature": _capture_signature,
    },
)
