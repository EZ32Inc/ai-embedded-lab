"""
ESP Remote JTAG backend for Instrument Action Model v0.1.

Supported actions:
  - flash         (wraps flash_bmda_gdbmi.run — ESP32JTAG acts as GDB server)
  - reset         (GDB batch: monitor reset run)
  - gpio_measure  (wraps esp32s3_dev_c_meter_tcp.measure_digital)
  - voltage_read  (wraps esp32s3_dev_c_meter_tcp.measure_voltage)

Instrument config keys used:
  connection.host       GDB/WebAPI host
  connection.gdb_port   GDB server port (default 4242)
  connection.web_port   Web/TCP API port (default 9000)
  config.gdb_cmd        GDB binary (default "arm-none-eabi-gdb")
  config.target_id      GDB attach target (default 1)
  config.gpio_channels  dict mapping channel name -> GPIO pin number(s)
  config.voltage_channels  dict mapping channel name -> ADC pin/config
"""

from __future__ import annotations

import time
from typing import Any

from ael.instruments.result import make_error_result, make_success_result


def _probe_cfg(instrument: dict) -> dict:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    return {
        "ip": str(conn.get("host") or "192.168.1.50"),
        "gdb_port": int(conn.get("gdb_port") or 4242),
        "gdb_cmd": str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb"),
    }


def _tcp_cfg(instrument: dict) -> dict:
    conn = instrument.get("connection") or {}
    return {
        "host": str(conn.get("host") or "192.168.1.50"),
        "port": int(conn.get("web_port") or conn.get("tcp_port") or 9000),
    }


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

    import io
    import contextlib
    import os
    if not os.path.exists(firmware):
        return make_error_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="invalid_request",
            message=f"firmware file not found: {firmware}",
        )

    from ael.adapters import flash_bmda_gdbmi

    cfg = instrument.get("config") or {}
    probe = _probe_cfg(instrument)
    fcfg = {
        "target_id": int(cfg.get("target_id") or 1),
        "timeout_s": int(request.get("timeout_s") or cfg.get("timeout_s") or 120),
        "gdb_launch_cmds": cfg.get("gdb_launch_cmds"),
        "speed_khz": cfg.get("speed_khz"),
    }

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
            summary=f"Flash completed via ESP JTAG in {elapsed:.1f}s",
            data={"elapsed_s": round(elapsed, 2)},
            logs=logs,
        )
    return make_error_result(
        action="flash",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="program_failed",
        message="ESP JTAG flash reported failure",
        retryable=True,
        logs=logs,
    )


def reset(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    host = str(conn.get("host") or "192.168.1.50")
    port = int(conn.get("gdb_port") or 4242)
    endpoint = f"{host}:{port}"

    import subprocess
    args = [
        str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb"),
        "-q", "--nx", "--batch",
        "-ex", "set pagination off",
        "-ex", "set confirm off",
        "-ex", f"target extended-remote {endpoint}",
        "-ex", "monitor swdp_scan",
        "-ex", f"attach {int(cfg.get('target_id') or 1)}",
        "-ex", "monitor reset run",
        "-ex", "disconnect",
    ]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        output = (result.stdout or "") + (result.stderr or "")
        lines = [l for l in output.splitlines() if l.strip()]
        return make_success_result(
            action="reset",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary="ESP JTAG reset issued",
            logs=lines,
        )
    except Exception as exc:
        return make_error_result(
            action="reset",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="connection_timeout",
            message=str(exc),
            retryable=True,
        )


def gpio_measure(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    """Measure a GPIO/digital channel via the ESP32JTAG HTTPS logic-analyser API.

    gpio_channels in instrument config map logical channel names to LA pin strings
    (e.g. "P0.0", "pa2"). The ESP32JTAG bit-samples the pin and returns edge counts,
    frequency estimate, and duty cycle at the data top level — no raw protocol diving.
    """
    channel = request.get("channel")
    mode = str(request.get("mode") or "toggle")
    duration_s = float(request.get("duration_s") or 1.0)

    cfg = instrument.get("config") or {}
    gpio_channels = cfg.get("gpio_channels") or {}
    if channel in gpio_channels:
        pin = str(gpio_channels[channel])
    elif channel is not None:
        pin = str(channel)
    else:
        return make_error_result(
            action="gpio_measure",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="invalid_request",
            message=f"request.channel is required. Available channels: {list(gpio_channels)}",
        )

    conn = instrument.get("connection") or {}
    probe_cfg = {
        "ip": str(conn.get("host") or "192.168.1.50"),
        "web_port": int(conn.get("web_port") or 443),
        "web_user": str(cfg.get("web_user") or "admin"),
        "web_pass": str(cfg.get("web_pass") or "admin"),
        "web_verify_ssl": bool(cfg.get("web_verify_ssl", False)),
        "web_suppress_ssl_warnings": True,
    }

    from ael.adapters import observe_gpio_pin
    import io
    import contextlib

    capture_out: dict = {}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ok = observe_gpio_pin.run(
                probe_cfg=probe_cfg,
                pin=pin,
                duration_s=duration_s,
                expected_hz=0,
                min_edges=0,
                max_edges=10_000_000,
                capture_out=capture_out,
                verify_edges=False,
            )
    except Exception as exc:
        return make_error_result(
            action="gpio_measure",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=str(exc),
            retryable=True,
        )

    logs = [l for l in buf.getvalue().splitlines() if l.strip()]

    if not ok:
        return make_error_result(
            action="gpio_measure",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=f"GPIO capture failed on pin '{pin}'",
            retryable=True,
            logs=logs,
        )

    # Normalise key values to data top level — AI does not need to inspect raw capture
    edges = int(capture_out.get("edges") or 0)
    window_s = float(capture_out.get("window_s") or duration_s)
    high = int(capture_out.get("high") or 0)
    low = int(capture_out.get("low") or 0)
    total_samples = high + low

    freq_hz = round(edges / 2.0 / window_s, 2) if (window_s > 0 and edges > 0) else 0.0
    duty = round(high / total_samples, 4) if total_samples > 0 else None

    summary_parts = [f"GPIO '{channel}' (pin={pin}): {edges} edges in {window_s:.3f}s"]
    if freq_hz > 0:
        summary_parts.append(f"~{freq_hz:.1f} Hz")
    if duty is not None:
        summary_parts.append(f"duty={duty:.3f}")
    summary = ", ".join(summary_parts)

    # raw excludes the binary blob (too large), keeps numeric diagnostics
    raw = {k: v for k, v in capture_out.items() if k != "blob"}

    return make_success_result(
        action="gpio_measure",
        instrument=instrument["name"],
        dut=context.get("dut"),
        summary=summary,
        data={
            "channel": channel,
            "pin": pin,
            "mode": mode,
            "duration_s": duration_s,
            "edges": edges,
            "freq_hz": freq_hz,
            "duty": duty,
            "window_s": window_s,
            "raw": raw,
        },
        logs=logs,
    )


def voltage_read(instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    channel = request.get("channel")

    cfg = instrument.get("config") or {}
    voltage_channels = cfg.get("voltage_channels") or {}
    if channel in voltage_channels:
        pin_spec = voltage_channels[channel]
    else:
        try:
            pin_spec = int(channel)
        except (ValueError, TypeError):
            return make_error_result(
                action="voltage_read",
                instrument=instrument["name"],
                dut=context.get("dut"),
                error_code="invalid_request",
                message=f"Unknown voltage channel '{channel}'. Available: {list(voltage_channels)}",
            )

    from ael.adapters import esp32s3_dev_c_meter_tcp as meter_tcp
    tcp = _tcp_cfg(instrument)

    try:
        result = meter_tcp.measure_voltage(tcp, pin=pin_spec)
    except Exception as exc:
        return make_error_result(
            action="voltage_read",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=str(exc),
            retryable=True,
        )

    if not result or result.get("type") == "error":
        return make_error_result(
            action="voltage_read",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=str(result),
            retryable=True,
        )

    voltage_v = None
    if isinstance(result.get("data"), dict):
        voltage_v = result["data"].get("voltage_v") or result["data"].get("voltage")

    return make_success_result(
        action="voltage_read",
        instrument=instrument["name"],
        dut=context.get("dut"),
        summary=f"Voltage on channel '{channel}': {voltage_v}V" if voltage_v is not None else f"Voltage read on channel '{channel}'",
        data={"channel": channel, "voltage_v": voltage_v, "raw": result},
    )


def invoke(action: str, instrument: dict, request: dict, context: dict) -> dict[str, Any]:
    if action == "flash":
        return flash(instrument, request, context)
    if action == "reset":
        return reset(instrument, request, context)
    if action == "gpio_measure":
        return gpio_measure(instrument, request, context)
    if action == "voltage_read":
        return voltage_read(instrument, request, context)
    return make_error_result(
        action=action,
        instrument=instrument.get("name"),
        dut=context.get("dut"),
        error_code="not_supported",
        message=f"ESP Remote JTAG backend does not support action '{action}'",
    )
