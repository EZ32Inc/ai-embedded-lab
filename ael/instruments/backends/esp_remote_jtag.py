"""
Legacy compatibility shim for the old ``esp_remote_jtag`` driver.

This module intentionally no longer owns its own mixed implementation.
Instead, it forwards actions to the current reference backends:

- ``flash`` / ``reset`` / ``gpio_measure`` -> ``esp32_jtag``
- ``voltage_read`` -> ``esp32_meter``

This keeps existing driver names runnable while avoiding further drift between
the old mixed backend and the newer package-style backends.
"""

from __future__ import annotations

from typing import Any

from ael.instruments.result import make_error_result

from .esp32_jtag import backend as esp32_jtag_backend
from .esp32_meter import backend as esp32_meter_backend


def _as_meter_instrument(instrument: dict[str, Any]) -> dict[str, Any]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    translated = dict(instrument)
    translated["driver"] = "esp32_meter"
    translated["connection"] = {
        "host": str(conn.get("host") or "192.168.1.50"),
        "tcp_port": int(conn.get("web_port") or conn.get("tcp_port") or 9000),
        "timeout_s": conn.get("timeout_s"),
    }
    translated["config"] = dict(cfg)
    return translated


def invoke(action: str, instrument: dict[str, Any], request: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if action in {"flash", "reset", "gpio_measure"}:
        return esp32_jtag_backend.invoke(action, instrument, request, context)
    if action == "voltage_read":
        return esp32_meter_backend.invoke(action, _as_meter_instrument(instrument), request, context)
    return make_error_result(
        action=action,
        instrument=instrument.get("name"),
        dut=context.get("dut"),
        error_code="not_supported",
        message=f"esp_remote_jtag legacy shim does not support action '{action}'",
    )
