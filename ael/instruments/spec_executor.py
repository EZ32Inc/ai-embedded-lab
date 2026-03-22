"""
Instrument Spec Executor — thin adapter layer.

Maps:  InstrumentSpec  →  action  →  existing backend

No refactoring of existing backends required.

Supported backends:

  network_rpc   — routes through ael.instruments.dispatcher.run_action()
                  The instrument must be declared in configs/action_model/.

  pyserial      — calls UsbUartBridgeBackend directly, using params from request.
                  Required request fields for pyserial:
                    uart_read:     port, baudrate (or baud), timeout (or duration_s)

  stlink_local  — calls st-flash directly (no GDB, no st-util, no network).
                  Binary: instruments/STLinkInstrument/install/bin/st-flash
                  Supported actions:
                    flash:  request.firmware (path), request.flash_addr (default 0x8000000)
                    reset:  no params required
                   uart_wait_for: port, baudrate (or baud), pattern, timeout (or timeout_s)

Usage:

    from ael.instruments.spec_loader import load_spec
    from ael.instruments.spec_executor import execute_spec_action

    spec = load_spec("configs/instrument_specs/uart0_local.yaml")
    result = execute_spec_action(spec, "uart_read", {"port": "/dev/ttyUSB0", "baudrate": 115200, "timeout": 2.0})
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .spec_loader import InstrumentSpec

# Local st-flash binary shipped with the repo
_STFLASH_BIN = (
    Path(__file__).resolve().parents[2]
    / "instruments" / "STLinkInstrument" / "install" / "bin" / "st-flash"
)
_STLINK_LIB_DIR = (
    Path(__file__).resolve().parents[2]
    / "instruments" / "STLinkInstrument" / "install" / "lib"
)


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
        elif backend == "stlink_local":
            return _execute_stlink_local(spec, action_name, request)
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


# ---------------------------------------------------------------------------
# backend: stlink_local
# ---------------------------------------------------------------------------

_STUTIL_BIN = (
    Path(__file__).resolve().parents[2]
    / "instruments" / "STLinkInstrument" / "install" / "bin" / "st-util"
)


def _stlink_env() -> dict[str, str]:
    """Build environment with LD_LIBRARY_PATH for local stlink install."""
    env = dict(os.environ)
    lib = str(_STLINK_LIB_DIR)
    current = str(env.get("LD_LIBRARY_PATH") or "")
    env["LD_LIBRARY_PATH"] = lib if not current else f"{lib}:{current}"
    return env


def _kill_stutil(port: int = 4242) -> None:
    """Kill any st-util process listening on the given port."""
    try:
        res = subprocess.run(["ps", "-ef"], capture_output=True, text=True, timeout=2)
    except Exception:
        return
    token = f"--listen_port {port}"
    for line in (res.stdout or "").splitlines():
        if "st-util" not in line or token not in line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            os.kill(int(parts[1]), 9)
        except Exception:
            pass
    time.sleep(0.5)


def _start_stutil(port: int = 4242) -> subprocess.Popen | None:
    """Start st-util in the background and wait briefly for it to be ready."""
    if not _STUTIL_BIN.exists():
        return None
    env = _stlink_env()
    try:
        proc = subprocess.Popen(
            [str(_STUTIL_BIN), "--listen_port", str(port), "--multi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        time.sleep(1.5)  # give st-util time to claim USB and start listening
        return proc
    except Exception:
        return None


def _execute_stlink_local(
    spec: InstrumentSpec,
    action_name: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Call st-flash directly — no GDB, no st-util, no network.

    flash: st-flash write <firmware> <flash_addr>
    reset: st-flash reset
    """
    if not _STFLASH_BIN.exists():
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": "stlink_local",
            "error": f"st-flash not found at {_STFLASH_BIN}",
        }

    env = _stlink_env()

    if action_name == "flash":
        firmware = str(request.get("firmware") or "")
        if not firmware:
            return {
                "ok": False,
                "action": action_name,
                "instrument": spec.id,
                "backend": "stlink_local",
                "error": "request.firmware is required for stlink_local flash",
            }
        if not Path(firmware).exists():
            return {
                "ok": False,
                "action": action_name,
                "instrument": spec.id,
                "backend": "stlink_local",
                "error": f"firmware file not found: {firmware}",
            }
        flash_addr = str(request.get("flash_addr") or "0x8000000")
        gdb_port = int(request.get("gdb_port") or 4242)

        # st-flash and st-util both need exclusive USB access.
        # Kill any running st-util before flash, then restart it afterwards
        # so the mailbox verify GDB step can connect.
        _kill_stutil(gdb_port)
        cmd = [str(_STFLASH_BIN), "write", firmware, flash_addr]

    elif action_name == "reset":
        cmd = [str(_STFLASH_BIN), "reset"]

    else:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": "stlink_local",
            "error": f"stlink_local does not support action '{action_name}'",
        }

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": "stlink_local",
            "error": f"st-flash timed out after 60s (action={action_name})",
        }
    except Exception as exc:
        return {
            "ok": False,
            "action": action_name,
            "instrument": spec.id,
            "backend": "stlink_local",
            "error": str(exc),
        }

    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    ok = proc.returncode == 0

    # After a successful flash, restart st-util so subsequent steps
    # (e.g. mailbox verify via GDB) can connect.
    if ok and action_name == "flash":
        _start_stutil(gdb_port)

    return {
        "ok": ok,
        "action": action_name,
        "instrument": spec.id,
        "backend": "stlink_local",
        "data": {
            "returncode": proc.returncode,
            "cmd": cmd,
        },
        "logs": [line for line in output.splitlines() if line.strip()],
        **({"error": output[:300] or f"st-flash exited {proc.returncode}"} if not ok else {}),
    }
