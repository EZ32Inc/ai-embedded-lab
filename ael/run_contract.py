from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class RunTermination:
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    SAFETY_ABORT = "safety_abort"

    ALL = (PASS, FAIL, TIMEOUT, SAFETY_ABORT)


@dataclass(frozen=True)
class RunRequest:
    probe_path: Optional[str]
    board_id: Optional[str]
    test_path: Optional[str]
    wiring: Optional[str] = None
    output_mode: str = "normal"
    skip_flash: bool = False
    no_build: bool = False
    verify_only: bool = False
    timeout_s: Optional[float] = None
    until_stage: Optional[str] = None
