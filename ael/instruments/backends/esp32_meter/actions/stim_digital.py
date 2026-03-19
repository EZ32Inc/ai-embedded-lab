from __future__ import annotations

from ..transport import Esp32MeterTransport


def run_stim_digital(transport: Esp32MeterTransport, request: dict[str, object]) -> dict[str, object]:
    response = transport.request("stim_digital", dict(request))
    raw = transport.ensure_ok(response, action="stim_digital")
    return {
        "status": "success",
        "action": "stim_digital",
        "data": {
            "gpio": request.get("gpio"),
            "mode": request.get("mode"),
            "raw": raw,
        },
        "logs": [],
    }

