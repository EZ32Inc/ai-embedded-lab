from __future__ import annotations

from typing import Any

from ..transport import UsbUartBridgeTransport


def run_uart_wait_for(transport: UsbUartBridgeTransport, params: dict[str, Any]) -> dict[str, Any]:
    if "pattern" not in params:
        return {
            "status": "failure",
            "action": "uart_wait_for",
            "error": {
                "code": "invalid_request",
                "message": "uart_wait_for requires 'pattern'",
            },
        }
    pattern = str(params.get("pattern") or "")
    timeout_s = float(params.get("timeout_s") or 5.0)
    data = transport.wait_for(pattern=pattern, timeout_s=timeout_s)
    if data["matched"]:
        return {
            "status": "success",
            "action": "uart_wait_for",
            "data": data,
            "logs": data["logs"],
        }
    return {
        "status": "failure",
        "action": "uart_wait_for",
        "error": {
            "code": "pattern_not_found",
            "message": f"Pattern '{pattern}' not found within {timeout_s}s",
        },
        "logs": data["logs"] + [f"Last captured: {data['capture_excerpt']}"],
        "data": data,
    }
