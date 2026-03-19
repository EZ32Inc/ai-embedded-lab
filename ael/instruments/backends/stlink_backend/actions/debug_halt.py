from __future__ import annotations

from typing import Any

from ..transport import endpoint_for, gdb_batch


def run_debug_halt(instrument: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    cfg = instrument.get("config") or {}
    endpoint = endpoint_for(instrument)
    skip_attach = bool(cfg.get("skip_attach", False))
    target_id = int(cfg.get("target_id") or 1)
    gdb_cmd = str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb")

    commands = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
    ]
    if not skip_attach:
        commands += ["monitor swdp_scan", f"attach {target_id}"]
    commands += ["monitor halt"]
    output = gdb_batch(endpoint, commands, timeout_s=20, gdb_cmd=gdb_cmd)
    return {
        "status": "success",
        "action": "debug_halt",
        "data": {},
        "logs": [line for line in output.splitlines() if line.strip()],
    }
