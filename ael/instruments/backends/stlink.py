"""
ST-Link backend for Instrument Action Model v0.1.

Supported actions:
  - flash               (wraps flash_bmda_gdbmi.run)
  - reset               (wraps flash_bmda_gdbmi — issues monitor reset run)
  - debug_halt          (GDB batch: halt the target)
  - debug_read_memory   (wraps check_mailbox_verify._gdb_read_mailbox)

Instrument config keys used (from instrument["connection"] and instrument["config"]):
  connection.host       GDB server host (default "127.0.0.1")
  connection.gdb_port   GDB server port (default 4242)
  config.gdb_cmd        GDB binary path (default "arm-none-eabi-gdb")
  config.target_id      GDB attach target (default 1)
  config.skip_attach    bool — omit swdp_scan/attach for st-util (default False)
  config.gdb_launch_cmds  list[str] — custom flash launch commands
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

from ael.instruments.result import make_error_result, make_success_result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _probe_cfg(instrument: dict) -> dict:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    return {
        "ip": str(conn.get("host") or "127.0.0.1"),
        "gdb_port": int(conn.get("gdb_port") or 4242),
        "gdb_cmd": str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb"),
    }


def _flash_cfg(instrument: dict, request: dict) -> dict:
    cfg = instrument.get("config") or {}
    return {
        "target_id": int(cfg.get("target_id") or 1),
        "timeout_s": int(request.get("timeout_s") or cfg.get("timeout_s") or 120),
        "gdb_launch_cmds": cfg.get("gdb_launch_cmds"),
        "speed_khz": cfg.get("speed_khz"),
        "reset_available": bool(cfg.get("reset_available", True)),
    }


def _gdb_batch(endpoint: str, commands: list[str], timeout_s: int = 15) -> tuple[bool, str]:
    """Run arm-none-eabi-gdb in batch mode with the given commands.

    Returns (success, combined_output).
    """
    args = ["arm-none-eabi-gdb", "-q", "--nx", "--batch"]
    for cmd in commands:
        args += ["-ex", cmd]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "GDB batch timed out"
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Action implementations
# ---------------------------------------------------------------------------

def flash(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    firmware = request.get("firmware")
    if not firmware:
        return make_error_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="invalid_request",
            message="request.firmware is required",
        )

    import os
    if not os.path.exists(firmware):
        return make_error_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="invalid_request",
            message=f"firmware file not found: {firmware}",
        )

    import contextlib
    import io
    from ael.adapters import flash_bmda_gdbmi

    probe = _probe_cfg(instrument)
    fcfg = _flash_cfg(instrument, request)

    t0 = time.monotonic()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ok = flash_bmda_gdbmi.run(probe, firmware, flash_cfg=fcfg)
    except Exception as exc:
        return make_error_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="program_failed",
            message=str(exc),
            retryable=True,
            logs=[l for l in buf.getvalue().splitlines() if l.strip()],
        )

    elapsed = time.monotonic() - t0
    logs = [l for l in buf.getvalue().splitlines() if l.strip()]
    if ok:
        return make_success_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary=f"Flash completed via ST-Link in {elapsed:.1f}s",
            data={"elapsed_s": round(elapsed, 2)},
            logs=logs,
        )
    return make_error_result(
        action="flash",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="program_failed",
        message="ST-Link flash reported failure",
        retryable=True,
        logs=logs,
    )


def reset(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or "127.0.0.1")
    port = int(conn.get("gdb_port") or 4242)
    endpoint = f"{host}:{port}"
    skip_attach = bool(cfg.get("skip_attach", False))

    cmds = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
    ]
    if not skip_attach:
        cmds += ["monitor swdp_scan", "attach 1"]
    cmds += ["monitor reset run", "disconnect"]

    ok, output = _gdb_batch(endpoint, cmds)
    if ok or "monitor reset run" in output.lower() or "reset" in output.lower():
        return make_success_result(
            action="reset",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary="ST-Link reset issued",
            logs=[line for line in output.splitlines() if line.strip()],
        )
    return make_error_result(
        action="reset",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="connection_timeout",
        message=f"ST-Link reset failed: {output[:200]}",
        retryable=True,
        logs=[line for line in output.splitlines() if line.strip()],
    )


def debug_halt(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or "127.0.0.1")
    port = int(conn.get("gdb_port") or 4242)
    endpoint = f"{host}:{port}"
    skip_attach = bool(cfg.get("skip_attach", False))
    target_id = int(cfg.get("target_id") or 1)

    cmds = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
    ]
    if not skip_attach:
        cmds += ["monitor swdp_scan", f"attach {target_id}"]
    cmds += ["monitor halt"]

    ok, output = _gdb_batch(endpoint, cmds, timeout_s=20)
    lines = [line for line in output.splitlines() if line.strip()]
    if ok:
        return make_success_result(
            action="debug_halt",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary="Target halted via ST-Link",
            logs=lines,
        )
    return make_error_result(
        action="debug_halt",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="connection_timeout",
        message=f"debug_halt failed: {output[:200]}",
        retryable=True,
        logs=lines,
    )


def debug_read_memory(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    address = request.get("address")
    length = request.get("length")

    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or "127.0.0.1")
    port = int(conn.get("gdb_port") or 4242)
    endpoint = f"{host}:{port}"
    skip_attach = bool(cfg.get("skip_attach", False))
    target_id = int(cfg.get("target_id") or 1)

    # Normalise address to int
    if isinstance(address, str):
        address_int = int(address, 16) if address.startswith("0x") else int(address, 0)
    else:
        address_int = int(address)

    # Number of 4-byte words to read
    words = max(1, int(length) // 4)
    hex_addr = hex(address_int)

    cmds = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
    ]
    if not skip_attach:
        cmds += ["monitor swdp_scan", f"attach {target_id}"]
    cmds += [f"x/{words}xw {hex_addr}", "disconnect"]

    ok, output = _gdb_batch(endpoint, cmds, timeout_s=20)
    lines = [line for line in output.splitlines() if line.strip()]

    if not ok and "0x" not in output:
        return make_error_result(
            action="debug_read_memory",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="connection_timeout",
            message=f"debug_read_memory failed: {output[:200]}",
            retryable=True,
            logs=lines,
        )

    # Extract hex words from the GDB x output
    import re
    hex_values = re.findall(r"0x[0-9a-fA-F]+", output)
    # Filter out the address labels (they appear at start of each row)
    data_words = []
    for line in lines:
        parts = re.findall(r"0x[0-9a-fA-F]+", line)
        if len(parts) > 1:
            data_words.extend(parts[1:])
        elif parts and line.strip().startswith(hex(address_int & ~0xF)):
            data_words.extend(parts[1:])

    return make_success_result(
        action="debug_read_memory",
        instrument=instrument["name"],
        dut=context.get("dut"),
        summary=f"Read {words} word(s) from {hex_addr}",
        data={
            "address": hex_addr,
            "length": length,
            "words": data_words or hex_values[:words],
            "raw_output": output[:500],
        },
        logs=lines,
    )


def invoke(action: str, instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    if action == "flash":
        return flash(instrument, request, context)
    if action == "reset":
        return reset(instrument, request, context)
    if action == "debug_halt":
        return debug_halt(instrument, request, context)
    if action == "debug_read_memory":
        return debug_read_memory(instrument, request, context)
    from ael.instruments.result import make_error_result as _err
    return _err(
        action=action,
        instrument=instrument.get("name"),
        dut=context.get("dut"),
        error_code="not_supported",
        message=f"ST-Link backend does not support action '{action}'",
    )
