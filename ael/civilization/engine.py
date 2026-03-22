"""AEL Civilization Engine — core module (internal AEL layer).

Architecture:
    AEL (pipeline, stage_explain, ...)
      ↓  (imports from ael.civilization)
    ael/civilization/engine.py          ← this file
      ↓  (uses ExperienceAPI)
    /nvme1t/work/codex/experience_engine/  ← external, unchanged

AEL never imports from experience_engine directly.
All Experience Engine interactions are encapsulated here.
"""

from __future__ import annotations

import sys
import os
import threading
from typing import List, Optional

_write_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Bootstrap: experience_engine uses flat imports — its directory must be in
# sys.path.  Path from ael/civilization/engine.py:
#   ../../../  →  /nvme1t/work/codex/
#   + experience_engine
# ---------------------------------------------------------------------------

_EE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "experience_engine")
)
if _EE_DIR not in sys.path:
    sys.path.insert(0, _EE_DIR)

try:
    import api as _ee_api_module  # experience_engine/api.py (flat import style)
    ExperienceAPI = _ee_api_module.ExperienceAPI
    _EE_AVAILABLE = True
except (ImportError, AttributeError):
    _EE_AVAILABLE = False

from ael.civilization.context import CivilizationContext
from ael.civilization.translator import (
    build_run_keyword,
    build_run_intent,
    build_run_raw,
    build_run_actions,
    ael_outcome_to_experience,
)
from ael.civilization import run_index

_DOMAIN = "engineering"


class CivilizationEngine:
    """AEL Civilization Engine: gateway between AEL and the Experience Engine.

    All methods degrade gracefully if the Experience Engine is unavailable.

    Public interface for AEL callers:
      get_context(board_id, test_name)          → CivilizationContext
      get_recommended_path(intent, context)     → List[dict]
      get_avoid_paths(intent, context)          → List[dict]
      get_relevant_skills(intent, context)      → List[dict]
      record_run(board_id, test_name, ok, ...)  → Optional[str]
      feedback(exp_id, correct, outcome)        → bool
      is_available()                            → bool
    """

    # ------------------------------------------------------------------
    # Primary interface: context retrieval (AEL pre-run)
    # ------------------------------------------------------------------

    @staticmethod
    def get_context(board_id: str, test_name: str) -> CivilizationContext:
        """Return all civilization assets relevant to an upcoming run.

        Includes prior successful runs and known avoid paths.
        Returns an empty CivilizationContext if the Experience Engine is
        unavailable (never raises).
        """
        ctx = CivilizationContext(board_id=board_id, test_name=test_name)

        # Always attach aggregated stats from local index (no EE needed)
        ctx.run_stats = run_index.get_run_stats(board_id, test_name)

        if not _EE_AVAILABLE:
            return ctx

        keyword = build_run_keyword(board_id, test_name)
        try:
            ctx.prior_runs = ExperienceAPI.query(
                keyword=keyword, domain=_DOMAIN, avoid=False
            ) or []
            ctx.avoid_paths = ExperienceAPI.query(
                keyword=keyword, domain=_DOMAIN, avoid=True
            ) or []
        except Exception:
            pass
        return ctx

    # ------------------------------------------------------------------
    # Structured queries — richer AEL callers can use these directly
    # ------------------------------------------------------------------

    @staticmethod
    def get_recommended_path(intent: str, context: dict) -> List[dict]:
        """Return past successful experiences relevant to this intent/context.

        Args:
            intent:  Free-text intent string, e.g. "verify rp2040_pico gpio"
            context: Dict with optional keys: board_id, test_name, domain

        Returns:
            List of experience dicts sorted by confidence (highest first).
            Empty list if nothing relevant or EE unavailable.
        """
        if not _EE_AVAILABLE:
            return []
        keyword = (
            context.get("board_id")
            or intent.split()[0]
            if intent.strip()
            else ""
        )
        try:
            return ExperienceAPI.query(
                keyword=keyword or None,
                domain=context.get("domain", _DOMAIN),
                outcome="success",
                avoid=False,
            ) or []
        except Exception:
            return []

    @staticmethod
    def get_avoid_paths(intent: str, context: dict) -> List[dict]:
        """Return known dangerous / failed experiences to avoid.

        Args:
            intent:  Free-text intent string
            context: Dict with optional keys: board_id, domain

        Returns:
            List of experience dicts marked avoid=True.
        """
        if not _EE_AVAILABLE:
            return []
        keyword = context.get("board_id") or (intent.split()[0] if intent.strip() else None)
        try:
            return ExperienceAPI.query(
                keyword=keyword,
                domain=context.get("domain", _DOMAIN),
                avoid=True,
            ) or []
        except Exception:
            return []

    @staticmethod
    def get_relevant_skills(intent: str, context: dict) -> List[dict]:
        """Return experiences tagged as skills/fixes relevant to this intent.

        In v0.1, a 'skill' is an experience tagged with 'fix' or 'decision'
        and outcome='success'.  Returns sorted by confidence.

        Args:
            intent:  Free-text intent string
            context: Dict with optional keys: board_id, domain

        Returns:
            List of skill experience dicts.
        """
        if not _EE_AVAILABLE:
            return []
        keyword = context.get("board_id") or (intent.split()[0] if intent.strip() else None)
        try:
            fix_skills = ExperienceAPI.query(
                keyword=keyword,
                domain=context.get("domain", _DOMAIN),
                tag="fix",
                avoid=False,
            ) or []
            decision_skills = ExperienceAPI.query(
                keyword=keyword,
                domain=context.get("domain", _DOMAIN),
                tag="decision",
                avoid=False,
            ) or []
            # merge, dedup by id, sort by confidence
            seen: set = set()
            merged = []
            for exp in fix_skills + decision_skills:
                eid = exp.get("id")
                if eid not in seen:
                    seen.add(eid)
                    merged.append(exp)
            merged.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
            return merged
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Record — called by AEL AFTER a run
    # ------------------------------------------------------------------

    @staticmethod
    def record_run(
        board_id: str,
        test_name: str,
        ok: bool,
        stages: List[str],
        failure_kind: str = "",
        description: str = "",
        source: str = "AEL",
    ) -> Optional[str]:
        """Record an AEL run result — aggregate if known, append if new.

        Logic:
          success + known signature → EE.feedback("correct") + index count++
          success + new signature   → EE.add() + index init
          failure + known kind      → EE.feedback("wrong")  + index count++
          failure + new kind        → EE.add() + index entry for this kind

        Thread-safe: _write_lock covers both EE and index writes.

        Returns:
            EE experience ID (canonical record for this outcome), or None.
        """
        outcome = ael_outcome_to_experience(ok, failure_kind)
        raw = build_run_raw(board_id, test_name, outcome, stages, failure_kind, description)
        intent = build_run_intent(board_id, test_name)
        actions = build_run_actions(stages)

        try:
            with _write_lock:
                if ok:
                    existing_id = run_index.get_success_exp_id(board_id, test_name)
                    if existing_id and _EE_AVAILABLE:
                        # Aggregate: strengthen existing success record
                        ExperienceAPI.feedback(exp_id=existing_id, feedback="correct")
                        run_index.record_success(board_id, test_name, existing_id)
                        return existing_id
                    elif _EE_AVAILABLE:
                        # First success: create EE record + index entry
                        exp = ExperienceAPI.add(
                            raw=raw, domain=_DOMAIN, intent=intent,
                            source=source, actions=actions, outcome=outcome, scope="task",
                        )
                        run_index.record_success(board_id, test_name, exp.id)
                        return exp.id
                    else:
                        run_index.record_success(board_id, test_name, "")
                        return None
                else:
                    existing_id = run_index.get_failure_exp_id(board_id, test_name, failure_kind)
                    if existing_id and _EE_AVAILABLE:
                        # Aggregate: same failure kind seen before
                        ExperienceAPI.feedback(exp_id=existing_id, feedback="wrong")
                        run_index.record_failure(board_id, test_name, failure_kind, existing_id, raw)
                        return existing_id
                    elif _EE_AVAILABLE:
                        # New failure kind: append to EE
                        exp = ExperienceAPI.add(
                            raw=raw, domain=_DOMAIN, intent=intent,
                            source=source, actions=actions, outcome=outcome, scope="task",
                        )
                        run_index.record_failure(board_id, test_name, failure_kind, exp.id, raw)
                        return exp.id
                    else:
                        run_index.record_failure(board_id, test_name, failure_kind, "", raw)
                        return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    @staticmethod
    def feedback(exp_id: str, correct: bool, outcome: Optional[str] = None) -> bool:
        """Apply feedback to adjust confidence on a recorded experience.

        Args:
            exp_id:  Experience ID from record_run()
            correct: True → confidence +0.1; False → confidence -0.1
            outcome: If "failed" and correct=False, also sets avoid=True

        Returns:
            True if applied, False otherwise.
        """
        if not _EE_AVAILABLE or not exp_id:
            return False
        try:
            return ExperienceAPI.feedback(
                exp_id=exp_id,
                feedback="correct" if correct else "wrong",
                outcome=outcome,
            )
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """True if the Experience Engine backend is reachable."""
        return _EE_AVAILABLE
