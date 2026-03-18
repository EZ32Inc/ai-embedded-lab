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
    try:
        ok = flash_bmda_gdbmi.run(probe, firmware, flash_cfg=fcfg)
    except Exception as exc:
        return make_error_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="program_failed",
            message=str(exc),
            retryable=True,
        )

    elapsed = time.monotonic() - t0
    if ok:
        return make_success_result(
            action="flash",
            instrument=instrument["name"],
            dut=context.get("dut"),
            summary=f"Flash completed via ESP JTAG in {elapsed:.1f}s",
            data={"elapsed_s": round(elapsed, 2)},
        )
    return make_error_result(
        action="flash",
        instrument=instrument["name"],
        dut=context.get("dut"),
        error_code="program_failed",
        message="ESP JTAG flash reported failure",
        retryable=True,
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
    channel = request.get("channel")
    mode = str(request.get("mode") or "toggle")
    duration_s = float(request.get("duration_s") or 0.5)
    duration_ms = int(duration_s * 1000)

    # Resolve channel name to GPIO pin number(s)
    cfg = instrument.get("config") or {}
    gpio_channels = cfg.get("gpio_channels") or {}
    if channel in gpio_channels:
        pin_spec = gpio_channels[channel]
    else:
        # Try to interpret channel as a bare pin number
        try:
            pin_spec = int(channel)
        except (ValueError, TypeError):
            return make_error_result(
                action="gpio_measure",
                instrument=instrument["name"],
                dut=context.get("dut"),
                error_code="invalid_request",
                message=f"Unknown GPIO channel '{channel}'. Available: {list(gpio_channels)}",
            )

    pins = [pin_spec] if isinstance(pin_spec, int) else list(pin_spec)

    from ael.adapters import esp32s3_dev_c_meter_tcp as meter_tcp
    tcp = _tcp_cfg(instrument)

    try:
        result = meter_tcp.measure_digital(tcp, pins=pins, duration_ms=duration_ms)
    except Exception as exc:
        return make_error_result(
            action="gpio_measure",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=str(exc),
            retryable=True,
        )

    if not result or result.get("type") == "error":
        return make_error_result(
            action="gpio_measure",
            instrument=instrument["name"],
            dut=context.get("dut"),
            error_code="measurement_failed",
            message=str(result),
            retryable=True,
        )

    return make_success_result(
        action="gpio_measure",
        instrument=instrument["name"],
        dut=context.get("dut"),
        summary=f"GPIO measurement on channel '{channel}' (mode={mode})",
        data={
            "channel": channel,
            "mode": mode,
            "pins": pins,
            "duration_s": duration_s,
            "raw": result,
        },
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
