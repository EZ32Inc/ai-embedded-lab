from __future__ import annotations

from typing import Any

from ..transport import Esp32MeterTransport


def run_voltage_read(transport: Esp32MeterTransport, request: dict[str, Any]) -> dict[str, Any]:
    gpio = request.get("gpio")
    avg = int(request.get("avg") or 16)
    response = transport.request(
        "voltage_read",
        {
            "gpio": gpio,
            "avg": avg,
        },
    )
    raw = transport.ensure_ok(response, action="voltage_read")
    voltage_v = raw.get("voltage_v")
    if voltage_v is None and isinstance(raw.get("data"), dict):
        voltage_v = raw["data"].get("voltage_v") or raw["data"].get("voltage")
    if voltage_v is None:
        voltage_v = raw.get("voltage")
    return {
        "status": "success",
        "action": "voltage_read",
        "data": {
            "gpio": gpio,
            "avg": avg,
            "voltage_v": voltage_v,
            "raw": raw,
        },
        "logs": [],
    }

