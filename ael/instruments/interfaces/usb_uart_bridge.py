from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from ael.instruments import usb_uart_bridge_daemon
from ael.instruments.interfaces.base import InstrumentProvider


NATIVE_API_PROTOCOL = usb_uart_bridge_daemon.NATIVE_API_PROTOCOL


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
    profile = dict(usb_uart_bridge_daemon.native_interface_profile())
    profile.setdefault("name", "USB UART Bridge Native Instrument Interface")
    profile.setdefault("role", "instrument_native_api")
    profile["instrument_family"] = "usb_uart_bridge"
    profile["instrument_identity"] = "uart_bridge_service"
    return profile



def _endpoint(manifest: Dict[str, Any]) -> str:
    communication = manifest.get("communication") if isinstance(manifest.get("communication"), dict) else {}
    endpoint = str(communication.get("endpoint") or "").strip()
    return endpoint



def _http_call(manifest: Dict[str, Any], path: str, *, payload: Optional[Dict[str, Any]] = None, timeout_s: float = 3.0) -> Dict[str, Any]:
    endpoint = _endpoint(manifest)
    if not endpoint:
        return _native_error("usb_uart_missing_endpoint", "usb-uart bridge endpoint missing", details={"path": path})
    url = endpoint if endpoint.startswith("http://") or endpoint.startswith("https://") else f"http://{endpoint}"
    url = f"{url}{path}"
    data = None
    headers: Dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib_request.urlopen(req, timeout=timeout_s) as resp:  # nosec B310 - local explicit endpoint
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib_error.URLError as exc:
        return _native_error("usb_uart_http_unreachable", str(exc), retryable=True, details={"path": path, "endpoint": endpoint})
    except Exception as exc:
        return _native_error("usb_uart_http_error", str(exc), retryable=True, details={"path": path, "endpoint": endpoint})
    if isinstance(raw, dict) and raw.get("status") in {"ok", "error"}:
        return raw
    if isinstance(raw, dict) and raw.get("ok") is True:
        return _native_ok(raw)
    return _native_error("usb_uart_action_failed", str((raw or {}).get("error") or f"usb-uart action failed at {path}"), retryable=True, details={"path": path, "response": raw})



def identify(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return _native_ok(
        {
            "device_id": str(manifest.get("id") or "usb_uart_bridge_daemon"),
            "device_type": "usb_uart_bridge_daemon",
            "instrument_family": "usb_uart_bridge",
            "instrument_role": "external_instrument",
            "model": str(manifest.get("model") or "USB UART Bridge Daemon"),
            "protocol_version": NATIVE_API_PROTOCOL,
            "endpoint": _endpoint(manifest),
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
            "params": item.get("params"),
            "exclusive": item.get("exclusive"),
        }
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "instrument_family": "usb_uart_bridge",
            "capability_families": {
                "uart_observe": {
                    "actions": ["read_uart"],
                    "surface": "bridge_http",
                },
                "serial_bridge": {
                    "actions": ["open", "close", "write_uart", "read_uart"],
                    "surface": "bridge_http",
                },
            },
            "capabilities": caps,
        }
    )



def get_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/status")
    if payload.get("status") != "ok":
        return payload
    data = (payload.get("data") or {}) if isinstance(payload.get("data"), dict) else {}
    return _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "instrument_family": "usb_uart_bridge",
            "endpoint": _endpoint(manifest),
            "bridge_status": data,
            "health_domains": {
                "tcp": {"ok": True},
                "bridge_service": {"ok": True},
                "uart_surface": {"ok": True},
            },
        }
    )



def doctor(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/doctor")
    if payload.get("status") == "ok":
        data = (payload.get("data") or {}) if isinstance(payload.get("data"), dict) else {}
        return _native_ok(
            {
                "protocol_version": NATIVE_API_PROTOCOL,
                "instrument_family": "usb_uart_bridge",
                "reachable": True,
                "checks": {
                    "tcp": {"ok": True},
                    "bridge_service": {"ok": True},
                    "uart_surface": {"ok": bool(data.get("ok", True))},
                    "doctor": data,
                },
                "lifecycle_boundary": {
                    "owned_by_native_api": ["identify", "get_capabilities", "get_status", "doctor", "open", "close", "write_uart", "read_uart"],
                    "owned_by_backend": [],
                    "out_of_scope": ["signal_capture", "firmware_programming"],
                },
            }
        )
    return _native_error(
        "usb_uart_doctor_failed",
        str(((payload.get("error") or {}).get("message") or "usb-uart doctor failed")),
        retryable=True,
        details={"endpoint": _endpoint(manifest), "doctor": payload},
    )



def open_uart(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return _http_call(manifest, "/open", payload={})



def close_uart(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return _http_call(manifest, "/close", payload={})



def write_uart(manifest: Dict[str, Any], *, text: Optional[str] = None, data_b64: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if text is not None:
        body["text"] = text
    if data_b64 is not None:
        body["data_b64"] = data_b64
    return _http_call(manifest, "/write", payload=body)



def read_uart(manifest: Dict[str, Any], *, size: int = 1024) -> Dict[str, Any]:
    return _http_call(manifest, "/read", payload={"size": int(size)})


PROVIDER = InstrumentProvider(
    family="usb_uart_bridge",
    native_interface_profile=native_interface_profile,
    identify=identify,
    get_capabilities=get_capabilities,
    get_status=get_status,
    doctor=doctor,
    actions={
        "open": open_uart,
        "close": close_uart,
        "write_uart": write_uart,
        "read_uart": read_uart,
    },
)
