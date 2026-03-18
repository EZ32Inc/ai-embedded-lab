from __future__ import annotations

from typing import Any

from ..errors import InvalidRequest, ResetFailure
from ..transport import Esp32JtagTransport


def run_reset(
    transport: Esp32JtagTransport,
    params: dict[str, Any],
) -> dict[str, Any]:
    reset_kind = params.get("reset_kind", "hard")
    if reset_kind not in {"hard", "soft", "line"}:
        raise InvalidRequest("reset_kind must be one of: hard, soft, line")
    response = transport.request(
        command="reset",
        payload={"reset_kind": reset_kind},
    )
    if response.get("ok") is not True:
        raise ResetFailure(response.get("message", "reset failed"))
    return {
        "status": "success",
        "action": "reset",
        "data": {
            "reset_kind": reset_kind,
            "elapsed_s": response.get("elapsed_s"),
            "method": response.get("method"),
        },
        "logs": response.get("logs", []),
    }
