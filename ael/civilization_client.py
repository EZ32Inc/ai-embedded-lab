"""AEL pipeline ↔ Civilization Engine adapter.

This is the only call-site in pipeline.py.  All Civilization Engine
logic lives in ael/civilization/.  pipeline.py stays clean.

AEL call path:
    pipeline.py
      → ael.civilization_client.print_rules()       ← before-run, always, high-priority
      → ael.civilization_client.query_context()     ← before-run, board+test specific
      → ael.civilization_client.record_run()        ← after-run
      → ael.civilization_client.reflect_on_run()    ← after-run, minimal reflection hook
      → ael.civilization_client.record_skill()      ← any time a fix is realized
          → ael.civilization.CivilizationEngine   (internal AEL module)
              → experience_engine                  (external, unchanged)

Before-run protocol (query_context output):
  ① run_stats        — N runs, S success / F failed, confidence
  ② relevant_skills  — known fix/decision skills for this board/domain
  ③ likely_pitfalls  — avoid_paths: paths marked dangerous
  ④ observation_focus — derived watch points from avoid_paths + failure history
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

try:
    from ael.civilization import CivilizationEngine, CivilizationContext
    _CE_AVAILABLE = True
except ImportError:
    _CE_AVAILABLE = False

_PHILOSOPHY_PATH = Path(__file__).parent / "civilization" / "data" / "ael_philosophy.json"


# ---------------------------------------------------------------------------
# Pre-run: high-priority AEL operating rules (always fires, no CE dependency)
# ---------------------------------------------------------------------------

def print_rules() -> None:
    """Print AEL core operating rules before every run.

    Fires unconditionally — independent of board/test history and CE availability.
    Rules are loaded from ael/civilization/data/ael_philosophy.json.
    """
    try:
        data = json.loads(_PHILOSOPHY_PATH.read_text())
        rules = data.get("rules", [])
        if rules:
            print("[AEL rules]")
            for rule in rules:
                print(f"  · {rule}")
    except Exception:
        pass


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
        print(f"[civilization] program run recorded → {board_id}/{test_name}: {outcome_str} (id={exp_id})")
        return exp_id
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Skill recording — call at any point during or after a run
# ---------------------------------------------------------------------------

def record_skill(
    trigger: str,
    fix: str,
    lesson: str,
    scope: str,
    board_id: str = "",
    source_ref: str = "",
) -> Optional[str]:
    """Record a reusable engineering skill into the Civilization Engine.

    Call this at the moment of realization — during or after a run, with no
    dependency on run outcome sequence.  Captured skills appear in
    query_context() → relevant_skills for future runs on the same board/scope.

    Args:
        trigger:    When this skill applies (symptom / trigger condition)
        fix:        Exact resolution (config, code, command)
        lesson:     Reusable rule derived from this experience
        scope:      Applicability scope, e.g. "stm32f4_discovery" / "all_stm32f4"
        board_id:   Specific board if narrower than scope (optional)
        source_ref: Origin reference, e.g. "docs/specs/stm32f401_bringup_report.md"

    Returns:
        EE experience ID or None.
    """
    if not _CE_AVAILABLE:
        return None
    try:
        exp_id = CivilizationEngine.record_skill(
            trigger=trigger,
            fix=fix,
            lesson=lesson,
            scope=scope,
            board_id=board_id,
            source_ref=source_ref,
        )
        print(f"[civilization] recorded skill → scope:{scope} (id={exp_id})")
        print(f"  trigger: {trigger[:80]}")
        print(f"  fix:     {fix[:80]}")
        return exp_id
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Post-run: minimal reflection hook
# ---------------------------------------------------------------------------

def reflect_on_run(
    board_id: str,
    test_name: str,
    was_first_success: bool,
    flash_instrument_spec: str = "",
    uart_instrument_spec: str = "",
) -> None:
    """Minimal post-run reflection stage.

    Checks whether this run produced something worth preserving as a skill.
    If triggered, calls record_skill() automatically with facts available
    from the pipeline.  Agent can call `ael civilization record-skill`
    separately to record richer, domain-specific insights.

    Trigger conditions (any one is sufficient):
      • was_first_success  — first passing run for this board+test combo
      • flash_instrument_spec  — non-standard flash path used
      • uart_instrument_spec   — non-standard UART observe path used
    """
    reasons: List[str] = []
    if was_first_success:
        reasons.append("first successful run on this board+test")
    if flash_instrument_spec:
        reasons.append(f"flash via instrument spec: {flash_instrument_spec}")
    if uart_instrument_spec:
        reasons.append(f"uart observe via instrument spec: {uart_instrument_spec}")

    if not reasons:
        return

    scope = board_id.split("_")[0] if board_id not in ("", "unknown") else "board"
    trigger = f"{board_id}/{test_name}: " + "; ".join(reasons)

    fix_parts = []
    if flash_instrument_spec:
        fix_parts.append(f"flash.instrument_spec={flash_instrument_spec}")
    if uart_instrument_spec:
        fix_parts.append(f"observe_uart.instrument_spec={uart_instrument_spec}")
    fix = "; ".join(fix_parts) if fix_parts else "standard pipeline — all stages passed"

    lesson = (
        f"Program {test_name} validated on {board_id}. "
        + " ".join(reasons) + "."
    )

    print(f"[civilization] reflection: {'; '.join(reasons)}")
    record_skill(
        trigger=trigger,
        fix=fix,
        lesson=lesson,
        scope=scope,
        board_id=board_id,
        source_ref=f"auto:reflect_on_run/{board_id}/{test_name}",
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def is_available() -> bool:
    return _CE_AVAILABLE
