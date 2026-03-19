from __future__ import annotations

import subprocess
from typing import Any

from .errors import ConnectionTimeout


def probe_cfg(instrument: dict[str, Any]) -> dict[str, Any]:
    conn = instrument.get("connection") or {}
    cfg = instrument.get("config") or {}
    return {
        "ip": str(conn.get("host") or "127.0.0.1"),
        "gdb_port": int(conn.get("gdb_port") or 4242),
        "gdb_cmd": str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb"),
    }


def flash_cfg(instrument: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    cfg = instrument.get("config") or {}
    return {
        "target_id": int(cfg.get("target_id") or 1),
        "timeout_s": int(request.get("timeout_s") or cfg.get("timeout_s") or 120),
        "gdb_launch_cmds": cfg.get("gdb_launch_cmds"),
        "speed_khz": cfg.get("speed_khz"),
        "reset_available": bool(cfg.get("reset_available", True)),
    }


def endpoint_for(instrument: dict[str, Any]) -> str:
    conn = instrument.get("connection") or {}
    host = str(conn.get("host") or "127.0.0.1")
    port = int(conn.get("gdb_port") or 4242)
    return f"{host}:{port}"


def gdb_batch(
    endpoint: str,
    commands: list[str],
    timeout_s: int = 15,
    gdb_cmd: str = "arm-none-eabi-gdb",
) -> str:
    args = [gdb_cmd, "-q", "--nx", "--batch"]
    for cmd in commands:
        args += ["-ex", cmd]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise ConnectionTimeout("GDB batch timed out") from exc
    except Exception as exc:
        raise ConnectionTimeout(str(exc)) from exc
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise ConnectionTimeout(output[:500] or "GDB batch failed")
    return output
