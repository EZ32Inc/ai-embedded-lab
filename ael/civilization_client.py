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
# Post-run: mandatory CE recording checklist (fires unconditionally)
# ---------------------------------------------------------------------------

def ce_recording_checklist(
    board_id: str,
    test_name: str,
    ok: bool,
    failed_step: str = "",
    error_summary: str = "",
    warnings: list = None,
    uart_errors: list = None,
) -> None:
    """Print and auto-record a structured CE audit block after every run.

    Fires unconditionally — pass OR fail.  Does NOT depend on CLAUDE.md or any
    AI instruction file.  Any AI tool (Claude, Codex, etc.) or human reading
    the run output will see the CE block and know exactly what to record.

    Auto-records:
      • run outcome (always)
      • failure pattern  (if failed_step is set)
      • warnings seen    (if any)

    The printed block also lists open questions that require human/AI insight
    to fill in (e.g. root cause, fix applied).  These cannot be auto-recorded
    because the pipeline has no semantic knowledge of WHY things failed.
    """
    warnings = warnings or []
    uart_errors = uart_errors or []
    outcome = "PASS" if ok else f"FAIL (stage={failed_step})"

    print()
    print("=" * 60)
    print("[CE] POST-RUN RECORDING BLOCK — action required")
    print("=" * 60)
    print(f"  board     : {board_id}")
    print(f"  test      : {test_name}")
    print(f"  outcome   : {outcome}")
    if error_summary:
        print(f"  error     : {error_summary}")
    if warnings:
        print(f"  warnings  : {len(warnings)} (see run log)")
        for w in warnings[:3]:
            print(f"              {str(w)[:100]}")
    if uart_errors:
        print(f"  uart_errs : {len(uart_errors)}")
        for e in uart_errors[:3]:
            print(f"              {str(e)[:100]}")
    print()

    # Auto-record the outcome fact (always — no AI judgment needed)
    if _CE_AVAILABLE:
        try:
            from ael.civilization import CivilizationEngine
            raw = (
                f"[AUTO] ael run {board_id}/{test_name}: {outcome}."
                + (f" stage={failed_step}." if failed_step else "")
                + (f" error={error_summary[:120]}." if error_summary else "")
            )
            CivilizationEngine._ee.add(raw=raw, domain="engineering", scope="task",
                                       outcome="success" if ok else "failure")
        except Exception:
            pass

    # Print the structured template that AI/human MUST fill in before closing the task.
    # Filling this template IS the CE recording — copy each populated line to
    # ExperienceAPI.add() or record_skill().  An unfilled template means knowledge loss.
    print("  REQUIRED: fill in the template below and record each non-empty line to CE.")
    print("  If nothing new: write 'CE: nothing new to record' explicitly.")
    print()
    print("  ## CE RECORDING TEMPLATE")
    print("  board_family : <e.g. esp32_classic / esp32c5 / stm32f4 / all>")
    print("  scope        : <task | board_family | pattern>")
    if not ok:
        print("  symptom      : <what was observed — error message, test output>")
        print("  root_cause   : <why it happened — driver bug, HW limitation, timing>")
        print("  fix          : <exact change made — file, config key, code snippet>")
    print("  constraint   : <wiring, GPIO, driver, SDK version restriction — or 'none'>")
    print("  lesson       : <reusable rule for next time>")
    print("  cross_board  : <yes/no — if yes, add [HIGH_PRIORITY] and scope=pattern>")
    print()
    print("  Paste populated template to: ExperienceAPI.add(raw=<lesson>, scope=<scope>)")
    print("  Cross-board patterns:        ExperienceAPI.add(raw='[HIGH_PRIORITY] ...', scope='pattern')")
    print("=" * 60)
    print()


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
