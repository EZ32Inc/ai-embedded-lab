from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from ael.instruments import usb_uart_bridge_daemon
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


NATIVE_API_PROTOCOL = usb_uart_bridge_daemon.NATIVE_API_PROTOCOL
USB_UART_CAPABILITIES = {
    "uart.session": {"actions": ["open", "close"], "surfaces": ["bridge_http"]},
    "uart.write": {"actions": ["write_uart"], "surfaces": ["bridge_http"]},
    "uart.read": {"actions": ["read_uart"], "surfaces": ["bridge_http"]},
    "uart.observe": {"actions": ["read_uart"], "surfaces": ["bridge_http"]},
}
STATUS_FALLBACK = {
    "strategy": "recover_bridge_service",
    "suggestion": "confirm the USB-UART bridge daemon is reachable before opening or using the serial session",
}
DOCTOR_FALLBACK = {
    "strategy": "restart_bridge_then_retry",
    "suggestion": "restore bridge reachability or restart the USB-UART daemon before retrying UART actions",
}
OPEN_UART_FALLBACK = {
    "strategy": "recover_bridge_then_reopen",
    "suggestion": "confirm the bridge daemon is reachable before opening the UART session",
}
CLOSE_UART_FALLBACK = {
    "strategy": "recover_bridge_then_close",
    "suggestion": "confirm the bridge daemon is reachable before closing the UART session",
}
WRITE_UART_FALLBACK = {
    "strategy": "recover_bridge_then_write",
    "suggestion": "restore bridge reachability before retrying UART writes",
}
READ_UART_FALLBACK = {
    "strategy": "recover_bridge_then_read",
    "suggestion": "restore bridge reachability before retrying UART reads",
}


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
    payload = _native_ok(
        {
            "protocol_version": NATIVE_API_PROTOCOL,
            "instrument_family": "usb_uart_bridge",
            "capabilities": caps,
        }
    )
    return wrap_legacy_action(
        payload,
        family="usb_uart_bridge",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="usb_uart_bridge",
            capabilities=USB_UART_CAPABILITIES,
            lifecycle_boundary={
                "owned_by_native_api": ["identify", "get_capabilities", "get_status", "doctor", "open", "close", "write_uart", "read_uart"],
                "owned_by_backend": [],
                "out_of_scope": ["signal_capture", "firmware_programming"],
            },
        ),
        failure_boundary="instrument_capabilities",
    )



def get_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/status")
    if payload.get("status") != "ok":
        return wrap_legacy_action(
            payload,
            family="usb_uart_bridge",
            action="get_status",
            failure_boundary="instrument_status",
            fallback=STATUS_FALLBACK,
        )
    data = (payload.get("data") or {}) if isinstance(payload.get("data"), dict) else {}
    return wrap_legacy_action(
        _native_ok(
            normalize_status_result(
                family="usb_uart_bridge",
                reachable=True,
                health_domains={
                    "tcp": {"ok": True},
                    "bridge_service": {"ok": True},
                    "uart_surface": {"ok": True},
                },
                endpoints={"bridge_http": _endpoint(manifest)} if _endpoint(manifest) else {},
                observations={"bridge_status": data} if data else {},
            )
        ),
        family="usb_uart_bridge",
        action="get_status",
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )



def doctor(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/doctor")
    if payload.get("status") == "ok":
        data = (payload.get("data") or {}) if isinstance(payload.get("data"), dict) else {}
        checks = {
            "tcp": {"ok": True},
            "bridge_service": {"ok": True},
            "uart_surface": {"ok": bool(data.get("ok", True))},
            "doctor": data,
        }
        wrapped = _native_ok(
            normalize_doctor_result(
                family="usb_uart_bridge",
                reachable=True,
                checks=checks,
                lifecycle_boundary={
                    "owned_by_native_api": ["identify", "get_capabilities", "get_status", "doctor", "open", "close", "write_uart", "read_uart"],
                    "owned_by_backend": [],
                    "out_of_scope": ["signal_capture", "firmware_programming"],
                },
                recovery_hint="restore bridge reachability or restart the USB-UART daemon before retrying UART actions",
                failure_boundary="instrument_health",
            )
        )
        return wrap_legacy_action(
            wrapped,
            family="usb_uart_bridge",
            action="doctor",
            failure_boundary="instrument_health",
            fallback=DOCTOR_FALLBACK,
        )
    return wrap_legacy_action(
        _native_error(
            "usb_uart_doctor_failed",
            str(((payload.get("error") or {}).get("message") or "usb-uart doctor failed")),
            retryable=True,
            details={"endpoint": _endpoint(manifest), "doctor": payload},
        ),
        family="usb_uart_bridge",
        action="doctor",
        failure_boundary="instrument_health",
        fallback=DOCTOR_FALLBACK,
    )




def _open_uart(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/open", payload={})
    return wrap_legacy_action(
        payload,
        family="usb_uart_bridge",
        action="open",
        requested={},
        success_mapper=lambda data: {
            "session_state": "open",
            "path": data.get("path", "/open"),
            "payload": data.get("payload", {}),
            "selected_serial_number": data.get("selected_serial_number"),
        },
        failure_boundary="uart_session",
        fallback=OPEN_UART_FALLBACK,
    )



def _close_uart(manifest: Dict[str, Any]) -> Dict[str, Any]:
    payload = _http_call(manifest, "/close", payload={})
    return wrap_legacy_action(
        payload,
        family="usb_uart_bridge",
        action="close",
        requested={},
        success_mapper=lambda data: {
            "session_state": "closed",
            "path": data.get("path", "/close"),
            "payload": data.get("payload", {}),
        },
        failure_boundary="uart_session",
        fallback=CLOSE_UART_FALLBACK,
    )



def _write_uart(manifest: Dict[str, Any], *, text: Optional[str] = None, data_b64: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if text is not None:
        body["text"] = text
    if data_b64 is not None:
        body["data_b64"] = data_b64
    payload = _http_call(manifest, "/write", payload=body)
    return wrap_legacy_action(
        payload,
        family="usb_uart_bridge",
        action="write_uart",
        requested=dict(body),
        success_mapper=lambda data: {
            "path": data.get("path", "/write"),
            "payload": data.get("payload", body),
            "bytes_written": data.get("bytes_written"),
            "text": text,
            "data_b64": data_b64,
        },
        failure_boundary="uart_io",
        fallback=WRITE_UART_FALLBACK,
    )



def _read_uart(manifest: Dict[str, Any], *, size: int = 1024) -> Dict[str, Any]:
    request = {"size": int(size)}
    payload = _http_call(manifest, "/read", payload=request)
    return wrap_legacy_action(
        payload,
        family="usb_uart_bridge",
        action="read_uart",
        requested=request,
        success_mapper=lambda data: {
            "path": data.get("path", "/read"),
            "payload": data.get("payload", request),
            "size": int(size),
            "text": data.get("text"),
            "data_b64": data.get("data_b64"),
            "bytes_read": data.get("bytes_read"),
        },
        failure_boundary="uart_io",
        fallback=READ_UART_FALLBACK,
    )



PROVIDER = InstrumentProvider(
    family="usb_uart_bridge",
    native_interface_profile=native_interface_profile,
    identify=identify,
    get_capabilities=get_capabilities,
    get_status=get_status,
    doctor=doctor,
    actions={
        "open": _open_uart,
        "close": _close_uart,
        "write_uart": _write_uart,
        "read_uart": _read_uart,
    },
)
