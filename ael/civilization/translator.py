"""Translator: AEL run concepts ↔ Experience Engine schema.

AEL thinks in terms of board_id, test_name, failure_kind, stages.
Experience Engine thinks in terms of raw text, domain, tags, outcome, intent.

This module handles the translation so neither AEL nor the Experience Engine
needs to know about the other's internal vocabulary.
"""

from __future__ import annotations

from typing import List, Optional


def build_run_keyword(board_id: str, test_name: str) -> str:
    """Primary keyword for querying past runs for this board/test combination.

    The raw text format is "[board_id] test_name: outcome ...".
    Use board_id alone as the keyword so it reliably matches "[board_id]".
    """
    return board_id.strip()


def build_run_intent(board_id: str, test_name: str) -> str:
    return f"verify {board_id} with {test_name}"


def build_run_raw(
    board_id: str,
    test_name: str,
    outcome: str,
    stages: List[str],
    failure_kind: str = "",
    description: str = "",
) -> str:
    """Build the raw text field for an experience record from an AEL run."""
    parts = [f"[{board_id}] {test_name}: {outcome}"]
    if stages:
        parts.append(f"stages: {', '.join(stages)}")
    if failure_kind:
        parts.append(f"failure: {failure_kind}")
    if description:
        parts.append(description)
    return " — ".join(parts)


def build_run_actions(stages: List[str]) -> List[str]:
    """Translate AEL stage list to experience engine action list."""
    return [f"stage:{s}" for s in stages]


def ael_outcome_to_experience(ok: bool, failure_kind: str = "") -> str:
    """Map AEL run success/failure to Experience Engine outcome vocabulary."""
    if ok:
        return "success"
    if failure_kind in ("preflight_failed", "probe_health"):
        return "partial"
    return "failed"


def experience_to_avoid_reason(exp: dict) -> Optional[str]:
    """Extract human-readable avoid reason from an experience record."""
    raw = str(exp.get("raw", ""))
    if not raw:
        return None
    return raw[:120]
