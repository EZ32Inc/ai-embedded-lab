from __future__ import annotations

import socket
from typing import Any, Dict, Optional

from ael.instruments import control_instrument_native_api
from ael.instruments.backends.stlink_backend.capability import CAPABILITIES


NATIVE_API_PROTOCOL = "ael.local_instrument.stlink_native_api.v0.1"


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
    communication = probe_cfg.get("communication") if isinstance(probe_cfg.get("communication"), dict) else {}
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
    if "gdb_remote" not in endpoints and ip and gdb_port is not None:
        endpoints["gdb_remote"] = f"{ip}:{gdb_port}"
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
        "name": "ST-Link Native Instrument Interface",
        "protocol": NATIVE_API_PROTOCOL,
        "role": "instrument_native_api",
        "instrument_family": "stlink",
        "instrument_identity": "local_debug_probe",
        "metadata_commands": ["identify", "get_capabilities", "get_status", "doctor"],
        "action_commands": ["preflight_probe", "program_firmware"],
        "status_domains": [
            "gdb_remote",
            "debug_attach",
        ],
        "lifecycle_scope": {
            "owned_by_native_api": ["identify", "get_capabilities", "get_status", "doctor", "preflight_probe"],
            "owned_by_backend": ["program_firmware", "reset", "debug_halt", "debug_read_memory"],
            "out_of_scope": ["signal_capture", "signal_generate", "provision"],
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
            "device_id": str(probe_cfg.get("instance_id") or probe_cfg.get("name") or "stlink"),
            "device_type": "local_debug_probe",
            "instrument_family": "stlink",
            "instrument_role": "control",
            "model": str(probe_cfg.get("name") or "ST-Link"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "communication_endpoints": endpoints,
            "capability_families": ["debug_remote", "debug_attach", "firmware_programming"],
        }
    )



def get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    capability_surfaces = probe_cfg.get("capability_surfaces") if isinstance(probe_cfg.get("capability_surfaces"), dict) else {}
    caps = CAPABILITIES.to_dict()
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "capability_families": {
                "debug_remote": {
                    "actions": ["program_firmware", "debug_halt", "debug_read_memory", "reset"],
                    "surface": capability_surfaces.get("swd", "gdb_remote"),
                    "owned_by": "stlink_backend",
                },
                "firmware_programming": {
                    "actions": ["program_firmware"],
                    "surface": capability_surfaces.get("swd", "gdb_remote"),
                    "owned_by": "control_instrument_native_api",
                },
                "debug_attach": {
                    "actions": ["preflight_probe"],
                    "surface": "instrument_native_api",
                    "owned_by": "stlink_native_api",
                },
            },
            "capabilities": caps,
        }
    )



def get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    endpoints = _endpoint_map(probe_cfg)
    gdb_remote = endpoints.get("gdb_remote")
    gdb_check = _tcp_check(gdb_remote)
    reachable = bool(gdb_check.get("ok"))
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "reachable": reachable,
            "endpoints": {"gdb_remote": gdb_check},
            "health_domains": {
                "gdb_remote": {
                    "ok": reachable,
                    "summary": "ST-Link GDB remote endpoint is reachable" if reachable else "ST-Link GDB remote endpoint is not reachable",
                },
                "debug_attach": {
                    "ok": None,
                    "state": "unverified",
                    "detail": "debug attach health is verified during preflight/programming",
                },
            },
        }
    )



def doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    status = get_status(probe_cfg)
    if status.get("status") != "ok":
        return _native_error("stlink_doctor_failed", "stlink doctor failed to collect status", retryable=True)
    status_data = (status.get("data") or {}) if isinstance(status.get("data"), dict) else {}
    gdb_check = ((status_data.get("endpoints") or {}).get("gdb_remote") or {}) if isinstance(status_data.get("endpoints"), dict) else {}
    payload = {
        "protocol_version": NATIVE_API_PROTOCOL,
        "reachable": bool(status_data.get("reachable")),
        "checks": {
            "gdb_remote": gdb_check,
            "debug_attach": {
                "ok": None,
                "state": "unverified",
                "detail": "ST-Link attach is verified during preflight/program_firmware",
            },
        },
        "lifecycle_boundary": native_interface_profile().get("lifecycle_scope"),
    }
    if payload["reachable"]:
        return _native_ok(payload)
    return _native_error("stlink_doctor_failed", "stlink instrument doctor failed", retryable=True, details=payload)



def preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    status = get_status(probe_cfg)
    if status.get("status") != "ok":
        return _native_error("stlink_preflight_failed", "stlink preflight failed", retryable=True)
    status_data = (status.get("data") or {}) if isinstance(status.get("data"), dict) else {}
    gdb_check = ((status_data.get("endpoints") or {}).get("gdb_remote") or {}) if isinstance(status_data.get("endpoints"), dict) else {}
    if bool(gdb_check.get("ok")):
        return _native_ok({"protocol_version": NATIVE_API_PROTOCOL, "preflight": {"gdb_remote": gdb_check}})
    return _native_error(
        "stlink_preflight_failed",
        "stlink preflight could not reach the GDB remote endpoint",
        retryable=True,
        details={"protocol_version": NATIVE_API_PROTOCOL, "preflight": {"gdb_remote": gdb_check}},
    )



def program_firmware(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.program_firmware(probe_cfg, **kwargs)
