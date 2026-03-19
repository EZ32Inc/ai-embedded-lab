from __future__ import annotations

from typing import Any, Callable

from ael.instruments.result import make_error_result, make_success_result

from .actions.uart_read import run_uart_read
from .actions.uart_wait_for import run_uart_wait_for
from .capability import CAPABILITIES
from .transport import TransportConfig, UsbUartBridgeTransport

ActionHandler = Callable[[UsbUartBridgeTransport, dict[str, Any]], dict[str, Any]]


class UsbUartBridgeBackend:
    def __init__(self, serial_port: str, baud: int = 115200, read_timeout_s: float = 1.0) -> None:
        self.transport = UsbUartBridgeTransport(
            TransportConfig(serial_port=serial_port, baud=baud, read_timeout_s=read_timeout_s)
        )
        self._handlers: dict[str, ActionHandler] = {
            "uart_read": run_uart_read,
            "uart_wait_for": run_uart_wait_for,
        }

    def capabilities(self) -> dict[str, Any]:
        return CAPABILITIES

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
            code = "connection_timeout"
            if "pyserial not installed" in str(exc):
                code = "program_failed"
            return {
                "status": "failure",
                "action": action,
                "error": {
                    "code": code,
                    "message": str(exc),
                    "details": {"exception_type": exc.__class__.__name__},
                },
            }


def _connection(instrument: dict[str, Any], request: dict[str, Any]) -> tuple[str, int, float]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    port = str(conn.get("serial_port") or conn.get("port") or "")
    if not port:
        raise RuntimeError("connection.serial_port not set in instrument config")
    baud = int(request.get("baud") or conn.get("baud") or cfg.get("baud") or 115200)
    timeout = float(cfg.get("read_timeout_s") or 1.0)
    return port, baud, timeout


def _bridge_result(result: dict[str, Any], instrument: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    action = str(result.get("action") or "")
    instrument_name = instrument.get("name")
    dut = context.get("dut")
    if result.get("status") == "success":
        data = (result.get("data") or {}) if isinstance(result.get("data"), dict) else {}
        logs = result.get("logs")
        if action == "uart_read":
            summary = f"UART read for {data.get('duration_s')}s — {len(data.get('lines') or [])} lines captured"
        else:
            summary = f"Pattern matched on UART output in {data.get('elapsed_s')}s"
        return make_success_result(
            action=action,
            instrument=instrument_name,
            dut=dut,
            summary=summary,
            data=data,
            logs=logs if isinstance(logs, list) else [],
        )
    error = (result.get("error") or {}) if isinstance(result.get("error"), dict) else {}
    logs = result.get("logs")
    return make_error_result(
        action=action,
        instrument=instrument_name,
        dut=dut,
        error_code=str(error.get("code") or "backend_error"),
        message=str(error.get("message") or "USB-UART bridge backend failed"),
        retryable=True,
        logs=logs if isinstance(logs, list) else None,
    )


def invoke(action: str, instrument: dict[str, Any], request: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    serial_port, baud, read_timeout_s = _connection(instrument, request)
    result = UsbUartBridgeBackend(
        serial_port=serial_port,
        baud=baud,
        read_timeout_s=read_timeout_s,
    ).execute(action, request)
    return _bridge_result(result, instrument, context)
