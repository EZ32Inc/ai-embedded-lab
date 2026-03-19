from __future__ import annotations

from typing import Any, Callable

from ael.instruments.result import make_error_result, make_success_result

from .actions.gpio_measure import run_gpio_measure
from .actions.stim_digital import run_stim_digital
from .actions.voltage_read import run_voltage_read
from .capability import CAPABILITIES
from .errors import error_code_for
from .transport import Esp32MeterTransport, TransportConfig

ActionHandler = Callable[[Esp32MeterTransport, dict[str, Any]], dict[str, Any]]


class Esp32MeterBackend:
    """IAM-style backend wrapper for the ESP32-S3 meter action path."""

    def __init__(self, host: str, port: int, timeout_s: float = 3.0) -> None:
        self.transport = Esp32MeterTransport(
            TransportConfig(host=host, port=port, timeout_s=timeout_s)
        )
        self._handlers: dict[str, ActionHandler] = {
            "gpio_measure": run_gpio_measure,
            "voltage_read": run_voltage_read,
            "stim_digital": run_stim_digital,
        }

    def capabilities(self) -> dict[str, Any]:
        return CAPABILITIES.to_dict()

    def supports_action(self, action: str) -> bool:
        return action in self._handlers

    def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        if action not in self._handlers:
            return {
                "status": "failure",
                "action": action,
                "error": {
                    "code": "unsupported_action",
                    "message": f"unsupported action: {action}",
                    "details": {"supported_actions": sorted(self._handlers.keys())},
                },
            }
        try:
            return self._handlers[action](self.transport, params)
        except Exception as exc:
            return {
                "status": "failure",
                "action": action,
                "error": {
                    "code": error_code_for(exc),
                    "message": str(exc),
                    "details": {"exception_type": exc.__class__.__name__},
                },
            }


def _connection(instrument: dict[str, Any]) -> tuple[str, int, float]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or conn.get("ip") or "192.168.4.1")
    port = int(conn.get("port") or conn.get("tcp_port") or 9000)
    timeout_s = float(cfg.get("timeout_s") or conn.get("timeout_s") or 3.0)
    return host, port, timeout_s


def _bridge_result(result: dict[str, Any], instrument: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    action = str(result.get("action") or "")
    instrument_name = instrument.get("name")
    dut = context.get("dut")
    status = result.get("status")
    if status == "success":
        data = result.get("data")
        logs = result.get("logs")
        summary = f"{action} completed via ESP32 meter"
        if action == "gpio_measure" and isinstance(data, dict):
            summary = f"gpio_measure completed via ESP32 meter on {data.get('channels')}"
        elif action == "voltage_read" and isinstance(data, dict):
            summary = f"voltage_read completed via ESP32 meter on GPIO {data.get('gpio')}"
        elif action == "stim_digital" and isinstance(data, dict):
            summary = f"stim_digital completed via ESP32 meter on GPIO {data.get('gpio')}"
        return make_success_result(
            action=action,
            instrument=instrument_name,
            dut=dut,
            summary=summary,
            data=data if isinstance(data, dict) else {},
            logs=logs if isinstance(logs, list) else [],
        )

    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    return make_error_result(
        action=action,
        instrument=instrument_name,
        dut=dut,
        error_code=str(error.get("code") or "backend_error"),
        message=str(error.get("message") or "ESP32 meter backend failed"),
        logs=[],
    )


def invoke(action: str, instrument: dict[str, Any], request: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    host, port, timeout_s = _connection(instrument)
    backend = Esp32MeterBackend(host=host, port=port, timeout_s=timeout_s)
    cfg = instrument.get("config") or {}
    translated = dict(request)
    if action == "gpio_measure":
        channel = translated.pop("channel", None)
        channels = translated.get("channels")
        if channels is None and channel is not None:
            translated["channels"] = [channel]
        translated["duration_ms"] = int(float(translated.pop("duration_s", 0.5)) * 1000) if "duration_s" in request else int(cfg.get("duration_ms") or translated.get("duration_ms") or 500)
    elif action == "voltage_read":
        channel = translated.get("channel")
        voltage_channels = cfg.get("voltage_channels") or {}
        if channel in voltage_channels:
            translated["gpio"] = voltage_channels[channel]
        elif channel is not None and "gpio" not in translated:
            translated["gpio"] = channel
    result = backend.execute(action, translated)
    return _bridge_result(result, instrument, context)

