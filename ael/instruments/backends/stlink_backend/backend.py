from __future__ import annotations

from typing import Any, Callable

from ael.instruments.result import make_error_result, make_success_result

from .actions import run_debug_halt, run_debug_read_memory, run_flash, run_reset
from .capability import CAPABILITIES
from .errors import error_code_for

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class StlinkBackend:
    """Reference-style backend wrapper for ST-Link."""

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {
            "flash": run_flash,
            "reset": run_reset,
            "debug_halt": run_debug_halt,
            "debug_read_memory": run_debug_read_memory,
        }

    def capabilities(self) -> dict[str, Any]:
        return CAPABILITIES.to_dict()

    def supports_action(self, action: str) -> bool:
        return action in self._handlers

    def execute(
        self,
        action: str,
        instrument: dict[str, Any],
        request: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = request or {}
        handler = self._handlers.get(action)
        if handler is None:
            return {
                "status": "failure",
                "action": action,
                "error": {
                    "code": "unsupported_action",
                    "message": f"unsupported action: {action}",
                    "details": {"supported_actions": sorted(self._handlers)},
                },
            }
        try:
            return handler(instrument, request)
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


def _bridge_result(result: dict[str, Any], instrument: dict, context: dict) -> dict[str, Any]:
    action = str(result.get("action") or "")
    instrument_name = instrument.get("name")
    dut = context.get("dut")
    if result.get("status") == "success":
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        logs = result.get("logs") if isinstance(result.get("logs"), list) else []
        summary = f"{action} completed via ST-Link"
        if action == "flash" and data.get("elapsed_s") is not None:
            summary = f"Flash completed via ST-Link in {data.get('elapsed_s')}s"
        elif action == "debug_read_memory" and data.get("address"):
            summary = f"Read memory via ST-Link at {data.get('address')}"
        elif action == "reset":
            summary = "ST-Link reset issued"
        elif action == "debug_halt":
            summary = "Target halted via ST-Link"
        return make_success_result(
            action=action,
            instrument=instrument_name,
            dut=dut,
            summary=summary,
            data=data,
            logs=logs,
        )

    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    return make_error_result(
        action=action,
        instrument=instrument_name,
        dut=dut,
        error_code=str(error.get("code") or "backend_error"),
        message=str(error.get("message") or "ST-Link backend failed"),
        retryable=str(error.get("code") or "") in {"connection_timeout", "program_failed"},
        logs=result.get("logs") if isinstance(result.get("logs"), list) else [],
    )


def invoke(action: str, instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    backend = StlinkBackend()
    result = backend.execute(action, instrument, request)
    return _bridge_result(result, instrument, context)
