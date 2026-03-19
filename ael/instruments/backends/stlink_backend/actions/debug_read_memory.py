from __future__ import annotations

import re
from typing import Any

from ..errors import InvalidRequest, MemoryReadFailed
from ..transport import endpoint_for, gdb_batch


def run_debug_read_memory(instrument: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if "address" not in request or "length" not in request:
        raise InvalidRequest("debug_read_memory requires address and length")

    address = request.get("address")
    length = request.get("length")
    cfg = instrument.get("config") or {}
    endpoint = endpoint_for(instrument)
    skip_attach = bool(cfg.get("skip_attach", False))
    target_id = int(cfg.get("target_id") or 1)
    gdb_cmd = str(cfg.get("gdb_cmd") or "arm-none-eabi-gdb")

    if isinstance(address, str):
        address_int = int(address, 16) if address.startswith("0x") else int(address, 0)
    else:
        address_int = int(address)
    words = max(1, int(length) // 4)
    hex_addr = hex(address_int)

    commands = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
    ]
    if not skip_attach:
        commands += ["monitor swdp_scan", f"attach {target_id}"]
    commands += [f"x/{words}xw {hex_addr}", "disconnect"]
    output = gdb_batch(endpoint, commands, timeout_s=20, gdb_cmd=gdb_cmd)
    lines = [line for line in output.splitlines() if line.strip()]
    if "0x" not in output:
        raise MemoryReadFailed("debug_read_memory produced no hex output")

    hex_values = re.findall(r"0x[0-9a-fA-F]+", output)
    data_words: list[str] = []
    for line in lines:
        parts = re.findall(r"0x[0-9a-fA-F]+", line)
        if len(parts) > 1:
            data_words.extend(parts[1:])
        elif parts and line.strip().startswith(hex(address_int & ~0xF)):
            data_words.extend(parts[1:])

    return {
        "status": "success",
        "action": "debug_read_memory",
        "data": {
            "address": hex_addr,
            "length": length,
            "words": data_words or hex_values[:words],
            "raw_output": output[:500],
        },
        "logs": lines,
    }
