from __future__ import annotations

from typing import Any

from ..transport import Esp32JtagTransport


def run_debug_read_memory(
    transport: Esp32JtagTransport,
    params: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "failure",
        "action": "debug_read_memory",
        "error": {
            "code": "not_implemented",
            "message": "debug_read_memory is reserved for Phase 2 and is not implemented yet",
            "details": {
                "phase": "phase2",
                "implemented": False,
            },
        },
    }
