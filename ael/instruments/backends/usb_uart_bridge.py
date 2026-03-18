"""
USB-UART bridge backend for Instrument Action Model v0.1.

Supported actions:
  - uart_read       Read UART output for a defined period.
  - uart_wait_for   Wait until UART output contains a given pattern.

Instrument config keys used:
  connection.serial_port   e.g. "/dev/ttyUSB0"
  connection.baud          default baud rate (default 115200)
  config.read_timeout_s    per-read timeout (default 1.0)

The backend opens the serial port directly using pyserial.  This avoids
depending on the USB-UART daemon process, which may or may not be running.
"""

from __future__ import annotations

import re
import time
from typing import Any

from ael.instruments.result import make_error_result, make_success_result


def _open_serial(instrument: dict, request: dict):
    try:
        import serial  # type: ignore
    except ImportError:
        return None, "pyserial not installed"

    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}

    port = str(conn.get("serial_port") or conn.get("port") or "")
    if not port:
        return None, "connection.serial_port not set in instrument config"

    baud = int(request.get("baud") or conn.get("baud") or cfg.get("baud") or 115200)
    timeout = float(cfg.get("read_timeout_s") or 1.0)

    try:
        ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        return ser, None
    except Exception as exc:
        return None, f"Failed to open {port}: {exc}"


def uart_read(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    duration_s = float(request.get("duration_s") or 2.0)

    ser, err = _open_serial(instrument, request)
    if err:
        return make_error_result(
            action="uart_read",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="connection_timeout",
            message=err,
            retryable=True,
        )

    logs: list[str] = []
    captured_lines: list[str] = []
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < duration_s:
            try:
                line = ser.readline().decode("utf-8", errors="replace")
            except Exception as exc:
                logs.append(f"read error: {exc}")
                break
            if line:
                captured_lines.append(line.rstrip())
    finally:
        ser.close()

    capture_text = "\n".join(captured_lines)
    return make_success_result(
        action="uart_read",
        instrument=instrument["name"],
        dut=context.get("dut"),
        summary=f"UART read for {duration_s}s — {len(captured_lines)} lines captured",
        data={"lines": captured_lines, "capture": capture_text, "duration_s": duration_s},
        logs=logs,
    )


def uart_wait_for(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    pattern = request.get("pattern")
    timeout_s = float(request.get("timeout_s") or 5.0)

    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        # Fall back to literal match if not valid regex
        compiled = re.compile(re.escape(str(pattern)))

    ser, err = _open_serial(instrument, request)
    if err:
        return make_error_result(
            action="uart_wait_for",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="connection_timeout",
            message=err,
            retryable=True,
        )

    logs: list[str] = [f"Waiting for pattern '{pattern}' (timeout={timeout_s}s)"]
    captured_lines: list[str] = []
    matched_line: str | None = None
    t0 = time.monotonic()

    try:
        while time.monotonic() - t0 < timeout_s:
            try:
                raw = ser.readline()
            except Exception as exc:
                logs.append(f"read error: {exc}")
                break
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip()
            captured_lines.append(line)
            if compiled.search(line):
                matched_line = line
                logs.append(f"Pattern matched: {line}")
                break
    finally:
        ser.close()

    elapsed = round(time.monotonic() - t0, 3)
    capture_excerpt = "\n".join(captured_lines[-10:])  # last 10 lines

    if matched_line is not None:
        return make_success_result(
            action="uart_wait_for",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary=f"Pattern matched on UART output in {elapsed}s",
            data={
                "pattern": pattern,
                "matched": True,
                "elapsed_s": elapsed,
                "matched_line": matched_line,
                "capture_excerpt": capture_excerpt,
            },
            logs=logs,
        )

    return make_error_result(
        action="uart_wait_for",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="pattern_not_found",
        message=f"Pattern '{pattern}' not found within {timeout_s}s",
        retryable=True,
        logs=logs + [f"Last captured: {capture_excerpt}"],
    )


def invoke(action: str, instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    if action == "uart_read":
        return uart_read(instrument, request, context)
    if action == "uart_wait_for":
        return uart_wait_for(instrument, request, context)
    return make_error_result(
        action=action,
        instrument=instrument.get("name"),
        dut=context.get("dut"),
        error_code="not_supported",
        message=f"USB-UART bridge backend does not support action '{action}'",
    )
