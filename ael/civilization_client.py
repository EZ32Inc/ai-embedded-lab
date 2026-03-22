"""AEL pipeline ↔ Civilization Engine adapter.

This is the only call-site in pipeline.py.  All Civilization Engine
logic lives in ael/civilization/.  pipeline.py stays clean.

AEL call path:
    pipeline.py
      → ael.civilization_client.query_context()
      → ael.civilization_client.record_run()
          → ael.civilization.CivilizationEngine   (internal AEL module)
              → experience_engine                  (external, unchanged)
"""

from __future__ import annotations

from typing import List, Optional

try:
    from ael.civilization import CivilizationEngine, CivilizationContext
    _CE_AVAILABLE = True
except ImportError:
    _CE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pre-run: query and surface civilization context
# ---------------------------------------------------------------------------

def query_context(board_id: str, test_name: str) -> Optional["CivilizationContext"]:
    """Query civilization context before a run and print it to stdout.

    Fire-and-forget: if unavailable, prints nothing and returns None.
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
# Post-run: record result
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

    Returns the experience ID or None.
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
        outcome_str = "success" if ok else (f"failed ({failure_kind})" if failure_kind else "failed")
        print(f"[civilization] recorded run → {board_id}/{test_name}: {outcome_str} (id={exp_id})")
        return exp_id
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def is_available() -> bool:
    return _CE_AVAILABLE
