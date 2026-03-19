from __future__ import annotations

from typing import Any

from ..transport import UsbUartBridgeTransport


def run_uart_read(transport: UsbUartBridgeTransport, params: dict[str, Any]) -> dict[str, Any]:
    duration_s = float(params.get("duration_s") or 2.0)
    data = transport.read_lines(duration_s=duration_s)
    return {
        "status": "success",
        "action": "uart_read",
        "data": {
            "lines": data["lines"],
            "capture": data["capture"],
            "duration_s": duration_s,
        },
        "logs": data["logs"],
    }
