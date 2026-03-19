from __future__ import annotations

from typing import Any

from ..transport import Esp32MeterTransport


def run_gpio_measure(transport: Esp32MeterTransport, request: dict[str, Any]) -> dict[str, Any]:
    channels = request.get("channels") or []
    response = transport.request(
        "gpio_measure",
        {
            "channels": channels,
            "duration_ms": int(request.get("duration_ms") or 500),
        },
    )
    raw = transport.ensure_ok(response, action="gpio_measure")
    return {
        "status": "success",
        "action": "gpio_measure",
        "data": {
            "channels": channels,
            "duration_ms": int(request.get("duration_ms") or 500),
            "raw": raw,
        },
        "logs": [],
    }

