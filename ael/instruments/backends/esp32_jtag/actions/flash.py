from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import InvalidRequest, ProgrammingFailure
from ..transport import Esp32JtagTransport


def run_flash(
    transport: Esp32JtagTransport,
    params: dict[str, Any],
) -> dict[str, Any]:
    firmware = params.get("firmware_path") or params.get("firmware")
    target = params.get("target")
    options = params.get("options", {})
    if not firmware:
        raise InvalidRequest("flash requires 'firmware' or 'firmware_path'")
    image = Path(str(firmware))
    if not image.exists():
        raise InvalidRequest(f"firmware image does not exist: {firmware}")
    response = transport.request(
        command="flash",
        payload={
            "firmware_path": str(image),
            "target": target,
            "options": options,
        },
    )
    if response.get("ok") is not True:
        raise ProgrammingFailure(response.get("message", "flash failed"))
    return {
        "status": "success",
        "action": "flash",
        "data": {
            "firmware_path": str(image),
            "target": target,
            "bytes_written": response.get("bytes_written"),
            "elapsed_s": response.get("elapsed_s"),
            "verified": response.get("verified"),
        },
        "logs": response.get("logs", []),
    }
