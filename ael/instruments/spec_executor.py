"""
Instrument Spec Executor — thin adapter layer.

Maps:  InstrumentSpec  →  action  →  existing backend

No refactoring of existing backends required.

Supported backends:

  network_rpc  — routes through ael.instruments.dispatcher.run_action()
                 The instrument must be declared in configs/action_model/.

  pyserial     — calls UsbUartBridgeBackend directly, using params from request.
                 Required request fields for pyserial:
                   uart_read:     port, baudrate (or baud), timeout (or duration_s)
                   uart_wait_for: port, baudrate (or baud), pattern, timeout (or timeout_s)

Usage:

    from ael.instruments.spec_loader import load_spec
    from ael.instruments.spec_executor import execute_spec_action

    spec = load_spec("configs/instrument_specs/uart0_local.yaml")
    result = execute_spec_action(spec, "uart_read", {"port": "/dev/ttyUSB0", "baudrate": 115200, "timeout": 2.0})
"""

from __future__ import annotations

from typing import Any

from .spec_loader import InstrumentSpec


def execute_spec_action(
    spec: InstrumentSpec,
    action_name: str,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action defined in a v1 instrument spec.

    Routes to the appropriate backend based on the action's `backend` field.

    Returns a standard result dict: {ok, action, instrument, backend, ...}
    """
    request = request or {}
    action = spec.get_action(action_name)
    if action is None:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "error": f"Action '{action_name}' not defined in spec for instrument '{spec.id}'",
        }

    backend = action.backend
    try:
        if backend == "network_rpc":
            return _execute_network_rpc(spec, action_name, request)
        elif backend == "pyserial":
            return _execute_pyserial(spec, action_name, request)
        else:
            return {
                "ok": False,
                "action": action_name,
                "instrument": spec.id,
                "backend": backend,
                "error": f"Unsupported backend '{backend}'",
            }
    except Exception as exc:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": backend,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# backend: network_rpc
# ---------------------------------------------------------------------------

def _execute_network_rpc(
    spec: InstrumentSpec,
    action_name: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Route through the existing action_model dispatcher.

    The instrument id in the spec must match an entry in configs/action_model/.
    """
    from .dispatcher import run_action

    raw = run_action(instrument=spec.id, action=action_name, request=request)
    return {
        "ok": raw.get("ok", False),
        "action": action_name,
        "instrument": spec.id,
        "backend": "network_rpc",
        **{k: v for k, v in raw.items() if k not in ("ok", "action", "instrument")},
    }


# ---------------------------------------------------------------------------
# backend: pyserial
# ---------------------------------------------------------------------------

def _execute_pyserial(
    spec: InstrumentSpec,
    action_name: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Call UsbUartBridgeBackend directly using params from request."""
    from .backends.usb_uart_bridge.backend import UsbUartBridgeBackend

    port = str(request.get("port") or "")
    if not port:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": "pyserial",
            "error": "request.port is required for pyserial backend",
        }

    baud = int(request.get("baudrate") or request.get("baud") or 115200)
    # Use timeout for read window or wait timeout
    timeout = float(request.get("timeout") or request.get("duration_s") or request.get("timeout_s") or 2.0)

    backend = UsbUartBridgeBackend(serial_port=port, baud=baud, read_timeout_s=timeout)

    # Build backend-specific request (remove transport params the backend doesn't need)
    inner_request = {k: v for k, v in request.items() if k not in ("port", "baudrate", "baud", "timeout")}
    if action_name == "uart_read":
        inner_request.setdefault("duration_s", timeout)
    elif action_name == "uart_wait_for":
        inner_request.setdefault("timeout_s", timeout)

    raw = backend.execute(action_name, inner_request)

    ok = raw.get("status") == "success"
    result: dict[str, Any] = {
        "ok": ok,
        "action": action_name,
        "instrument": spec.id,
        "backend": "pyserial",
    }
    if ok:
        result["data"] = raw.get("data") or {}
        result["logs"] = raw.get("logs") or []
    else:
        error = raw.get("error") or {}
        result["error"] = error.get("message") or str(error)
    return result
