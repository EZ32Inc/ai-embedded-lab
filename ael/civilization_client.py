"""AEL ↔ Civilization Engine thin adapter.

AEL calls this module; it never imports from experience_engine directly.
All Experience Engine interactions go through civilization_engine.api.

This module adds:
- sys.path bootstrap for the civilization_engine package
- AEL-specific helpers (stage list extraction, failure_kind lookup)
- Logging integration (prints to console in normal pipeline output format)
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

# ---------------------------------------------------------------------------
# Bootstrap: make civilization_engine importable
# ---------------------------------------------------------------------------

_CE_PARENT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _CE_PARENT not in sys.path:
    sys.path.insert(0, _CE_PARENT)

try:
    from civilization_engine.api import CivilizationEngine
    from civilization_engine.context import CivilizationContext
    _CE_AVAILABLE = True
except ImportError:
    _CE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pre-run: query
# ---------------------------------------------------------------------------

def query_context(board_id: str, test_name: str) -> Optional["CivilizationContext"]:
    """Query civilization context before a run and print it to stdout.

    This is a fire-and-forget call: if the Civilization Engine is unavailable
    it prints nothing and returns None. AEL pipeline continues normally.
    """
    if not _CE_AVAILABLE:
        return None
    try:
        ctx = CivilizationEngine.get_context(board_id=board_id, test_name=test_name)
        for line in ctx.summary_lines():
            print(line)
        return ctx
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Post-run: record
# ---------------------------------------------------------------------------

def record_run(
    board_id: str,
    test_name: str,
    ok: bool,
    stages: List[str],
    failure_kind: str = "",
    description: str = "",
) -> Optional[str]:
    """Record an AEL run result into the Civilization Engine.

    Returns the experience ID (for optional later feedback) or None.
    """
    if not _CE_AVAILABLE:
        return None
    try:
        exp_id = CivilizationEngine.record_run(
            board_id=board_id,
            test_name=test_name,
            ok=ok,
            stages=stages,
            failure_kind=failure_kind,
            description=description,
        )
        outcome_str = "success" if ok else f"failed ({failure_kind})" if failure_kind else "failed"
        print(f"[civilization] recorded run → {board_id}/{test_name}: {outcome_str} (id={exp_id})")
        return exp_id
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_available() -> bool:
    return _CE_AVAILABLE
