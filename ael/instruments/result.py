"""
Standard result helpers for Instrument Action Model v0.1.

Every action must return a result dict with a common shape that AI agents can
depend on.
"""

from __future__ import annotations

from typing import Any


def make_success_result(
    *,
    action: str,
    instrument: str,
    dut: str | None = None,
    summary: str = "",
    data: dict | None = None,
    logs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "action": action,
        "instrument": instrument,
        "dut": dut,
        "summary": summary,
        "data": data or {},
        "logs": logs or [],
    }


def make_error_result(
    *,
    action: str,
    instrument: str | None = None,
    dut: str | None = None,
    error_code: str,
    message: str,
    retryable: bool = False,
    logs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "action": action,
        "instrument": instrument,
        "dut": dut,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "logs": logs or [],
    }
