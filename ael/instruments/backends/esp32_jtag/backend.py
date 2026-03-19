from __future__ import annotations

from typing import Any, Callable

from ael.instruments.result import make_error_result, make_success_result

from .actions.debug_halt import run_debug_halt
from .actions.debug_read_memory import run_debug_read_memory
from .actions.flash import run_flash
from .actions.gpio_measure import run_gpio_measure
from .actions.reset import run_reset
from .capability import CAPABILITIES
from .errors import error_code_for
from .transport import Esp32JtagTransport, TransportConfig

ActionHandler = Callable[[Esp32JtagTransport, dict[str, Any]], dict[str, Any]]


class Esp32JtagBackend:
    """IAM-facing reference backend wrapper for ESP32-JTAG."""

    def __init__(self, host: str, port: int, timeout_s: float = 10.0) -> None:
        self.transport = Esp32JtagTransport(
            TransportConfig(host=host, port=port, timeout_s=timeout_s)
        )
        self._handlers: dict[str, ActionHandler] = {
            "debug_halt": run_debug_halt,
            "debug_read_memory": run_debug_read_memory,
            "flash": run_flash,
            "gpio_measure": run_gpio_measure,
            "reset": run_reset,
        }
        self._implemented_actions = {"flash", "gpio_measure", "reset"}

    def capabilities(self) -> dict[str, Any]:
        return CAPABILITIES.to_dict()

    def supports_action(self, action: str) -> bool:
        return action in self._implemented_actions

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
        handler = self._handlers[action]
        try:
            return handler(self.transport, params)
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


def _connection(instrument: dict) -> tuple[str, int, float]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or "192.168.1.50")
    port = int(conn.get("port") or conn.get("tcp_port") or conn.get("gdb_port") or 5555)
    timeout_s = float(cfg.get("timeout_s") or conn.get("timeout_s") or 10.0)
    return host, port, timeout_s


def _bridge_result(result: dict[str, Any], instrument: dict, context: dict) -> dict[str, Any]:
    action = str(result.get("action") or "")
    instrument_name = instrument.get("name")
    dut = context.get("dut")
    status = result.get("status")
    if status == "success":
        data = result.get("data")
        logs = result.get("logs")
        summary = f"{action} completed via ESP32-JTAG"
        if isinstance(data, dict):
            method = data.get("method")
            if method:
                summary = f"{action} completed via ESP32-JTAG ({method})"
            elif action == "flash" and data.get("firmware_path"):
                summary = f"flash completed via ESP32-JTAG for {data.get('firmware_path')}"
            elif action == "gpio_measure" and data.get("channels"):
                summary = f"gpio_measure completed via ESP32-JTAG on {data.get('channels')}"
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
        message=str(error.get("message") or "ESP32-JTAG backend failed"),
        logs=[],
    )


def invoke(action: str, instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    host, port, timeout_s = _connection(instrument)
    backend = Esp32JtagBackend(host=host, port=port, timeout_s=timeout_s)
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    backend.transport = Esp32JtagTransport(
        TransportConfig(
            host=host,
            port=port,
            timeout_s=timeout_s,
            compat_mode=True,
            gdb_port=int(conn.get("gdb_port") or port),
            web_port=int(conn.get("web_port") or conn.get("tcp_port") or 443),
            gdb_cmd=str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb"),
            target_id=int(cfg.get("target_id") or 1),
            gdb_launch_cmds=cfg.get("gdb_launch_cmds"),
            speed_khz=(int(cfg.get("speed_khz")) if cfg.get("speed_khz") is not None else None),
            gpio_channels=(dict(cfg.get("gpio_channels") or {})),
            web_user=str(cfg.get("web_user") or "admin"),
            web_pass=str(cfg.get("web_pass") or "admin"),
            web_verify_ssl=bool(cfg.get("web_verify_ssl", False)),
        )
    )
    result = backend.execute(action, request)
    return _bridge_result(result, instrument, context)
