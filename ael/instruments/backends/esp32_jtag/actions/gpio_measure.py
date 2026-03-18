from __future__ import annotations

from typing import Any

from ..errors import InvalidRequest, MeasurementFailure
from ..transport import Esp32JtagTransport


def run_gpio_measure(
    transport: Esp32JtagTransport,
    params: dict[str, Any],
) -> dict[str, Any]:
    channels = params.get("channels")
    if not channels:
        single = params.get("channel")
        if single is not None:
            channels = [single]
    measurement_type = params.get("measurement_type") or params.get("mode") or "signature"
    settle_ms = int(params.get("settle_ms") or 0)
    if not channels or not isinstance(channels, list):
        raise InvalidRequest("gpio_measure requires non-empty 'channels' list")
    response = transport.request(
        command="gpio_measure",
        payload={
            "channels": channels,
            "measurement_type": measurement_type,
            "settle_ms": settle_ms,
        },
    )
    if response.get("ok") is not True:
        raise MeasurementFailure(response.get("message", "gpio_measure failed"))
    return {
        "status": "success",
        "action": "gpio_measure",
        "data": {
            "measurement_type": measurement_type,
            "channels": channels,
            "values": response.get("values"),
            "summary": response.get("summary"),
            "pass_hint": response.get("pass_hint"),
            "elapsed_s": response.get("elapsed_s"),
        },
        "logs": response.get("logs", []),
    }
