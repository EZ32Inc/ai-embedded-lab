from __future__ import annotations

from typing import Any

from ..transport import Esp32JtagTransport


def run_debug_halt(
    transport: Esp32JtagTransport,
    params: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "failure",
        "action": "debug_halt",
        "error": {
            "code": "not_implemented",
            "message": "debug_halt is reserved for Phase 2 and is not implemented yet",
            "details": {
                "phase": "phase2",
                "implemented": False,
            },
        },
    }
