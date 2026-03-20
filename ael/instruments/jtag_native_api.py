from __future__ import annotations

import socket
from typing import Any, Dict, Optional

from ael.adapters import preflight as preflight_adapter
from ael.instruments import control_instrument_native_api


NATIVE_API_PROTOCOL = "ael.local_instrument.jtag_native_api.v0.1"


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


def get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
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
                    "owned_by": "jtag_native_api",
                },
                "firmware_programming": {
                    "actions": ["program_firmware"],
                    "surface": capability_surfaces.get("swd", "gdb_remote"),
                    "owned_by": "jtag_native_api",
                },
                "capture_signature": {
                    "actions": ["capture_signature"],
                    "surface": capability_surfaces.get("gpio_in", "web_api"),
                    "owned_by": "jtag_native_api",
                },
            },
        }
    )


def get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
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
                "capture_subsystem": {
                    "ok": bool(control_check.get("ok")),
                    "dependency": "web_api",
                },
                "monitor_targets": {
                    "ok": None,
                    "state": "unverified",
                    "detail": "monitor target enumeration runs during doctor/preflight",
                },
            },
        }
    )


def doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    status = get_status(probe_cfg)
    if status.get("status") != "ok":
        return _native_error("jtag_doctor_failed", "jtag doctor failed to collect status", retryable=True)
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
            "capture_subsystem": {
                "ok": la_ok,
                "detail": "logic-analyzer self-test passed" if la_ok else "logic-analyzer self-test failed",
            },
            "monitor_targets": {
                "ok": monitor_ok,
                "targets": monitor_targets,
            },
            "preflight": {"ok": bool(ok), "detail": preflight_info},
        },
        "lifecycle_boundary": native_interface_profile().get("lifecycle_scope"),
    }
    if ok:
        return _native_ok(payload)
    return _native_error("jtag_doctor_failed", "jtag instrument doctor failed", retryable=True, details=payload)


def preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ok, info = preflight_adapter.run(probe_cfg)
    if ok:
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "preflight": info or {},
            }
        )
    return _native_error(
        "jtag_preflight_failed",
        "jtag instrument preflight failed",
        retryable=True,
        details={
            "protocol_version": NATIVE_API_PROTOCOL,
            "preflight": info or {},
        },
    )


def program_firmware(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.program_firmware(probe_cfg, **kwargs)



def capture_signature(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.capture_signature(probe_cfg, **kwargs)
