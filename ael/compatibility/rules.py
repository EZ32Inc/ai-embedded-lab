"""Atomic compatibility check rules.

Each function checks one dimension of compatibility and returns
(satisfied: bool, reason: str).  The resolver composes these.
"""

from __future__ import annotations

from typing import FrozenSet, Tuple

from ael.compatibility.model import Requirement


def check_capability_present(
    requirement: Requirement,
    provided: FrozenSet[str],
) -> Tuple[bool, str]:
    """Check that the required capability type is among those provided.

    Returns:
        (True, reason) if satisfied; (False, reason) if not.
    """
    cap_type = requirement.type
    if cap_type in provided:
        return True, f"instrument provides '{cap_type}'"
    return False, f"instrument does not provide '{cap_type}'"


def check_required_set(
    requirements: list[Requirement],
    provided: FrozenSet[str],
) -> Tuple[list[str], list[str], list[str]]:
    """Check all requirements against the provided capability set.

    Returns:
        (matched, missing, warnings) — each is a list of descriptive strings.
    """
    matched: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []

    for req in requirements:
        ok, reason = check_capability_present(req, provided)
        if ok:
            matched.append(reason)
        elif req.optional:
            warnings.append(f"optional capability '{req.type}' not available — {reason}")
        else:
            missing.append(f"required capability '{req.type}' missing — {reason}")

    return matched, missing, warnings
