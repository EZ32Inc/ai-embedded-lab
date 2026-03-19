from __future__ import annotations

import contextlib
import io
import os
import time
from typing import Any

from ael.adapters import flash_bmda_gdbmi

from ..errors import InvalidRequest, ProgramFailed
from ..transport import flash_cfg, probe_cfg


def run_flash(instrument: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    firmware = request.get("firmware")
    if not firmware:
        raise InvalidRequest("request.firmware is required")
    if not os.path.exists(firmware):
        raise InvalidRequest(f"firmware file not found: {firmware}")

    probe = probe_cfg(instrument)
    fcfg = flash_cfg(instrument, request)

    t0 = time.monotonic()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ok = flash_bmda_gdbmi.run(probe, firmware, flash_cfg=fcfg)
    except Exception as exc:
        logs = [line for line in buf.getvalue().splitlines() if line.strip()]
        raise ProgramFailed(str(exc) or "ST-Link flash failed") from exc

    logs = [line for line in buf.getvalue().splitlines() if line.strip()]
    if not ok:
        raise ProgramFailed("ST-Link flash reported failure")
    return {
        "status": "success",
        "action": "flash",
        "data": {
            "firmware_path": str(firmware),
            "elapsed_s": round(time.monotonic() - t0, 2),
        },
        "logs": logs,
    }
