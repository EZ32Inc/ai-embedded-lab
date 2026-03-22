"""CivilizationContext — structured asset bundle returned to AEL before a run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CivilizationContext:
    """Civilization assets relevant to an upcoming AEL run.

    AEL receives this before planning/execution and uses it to:
    - know what has worked before (prior_runs)
    - know what has failed before and should be avoided (avoid_paths)
    - surface aggregated run statistics (run_stats)
    - surface known fix/decision skills (relevant_skills)

    summary_lines() surfaces four sections:
      ① run_stats        — how many times, what confidence
      ② relevant_skills  — known fixes / decisions for this board/domain
      ③ likely_pitfalls  — avoid_paths: paths marked dangerous
      ④ observation_focus — derived: what to actively watch this run
    """

    board_id: str
    test_name: str

    # EE records for this board+test (excluding avoid paths)
    prior_runs: List[dict] = field(default_factory=list)

    # Experiences marked avoid=True (dangerous paths, known failures)
    avoid_paths: List[dict] = field(default_factory=list)

    # Aggregated statistics from run_index (success_count, failure_count, confidence, last_seen)
    run_stats: dict = field(default_factory=dict)

    # Known fix/decision skills relevant to this board/domain (from get_relevant_skills)
    relevant_skills: List[dict] = field(default_factory=list)

    @property
    def has_prior_success(self) -> bool:
        return self.run_stats.get("success_count", 0) > 0 or any(
            r.get("outcome") == "success" for r in self.prior_runs
        )

    @property
    def has_avoid_paths(self) -> bool:
        return len(self.avoid_paths) > 0

    def summary_lines(self) -> List[str]:
        """Human-readable lines for pipeline logging.

        Sections (only printed if non-empty):
          ① run_stats        — N runs, S success / F failed, confidence
          ② relevant_skills  — known fix/decision skills
          ③ likely_pitfalls  — avoid_paths
          ④ observation_focus — derived watch points
        """
        lines = []
        stats = self.run_stats
        has_any = stats or self.prior_runs or self.avoid_paths or self.relevant_skills

        if not has_any:
            lines.append(
                f"[civilization] no prior experience for {self.board_id}/{self.test_name}"
            )
            return lines

        # ① run_stats
        if stats:
            s = stats.get("success_count", 0)
            f = stats.get("failure_count", 0)
            conf = stats.get("confidence", 0.5)
            total = s + f
            lines.append(
                f"[civilization] {self.board_id}/{self.test_name}: "
                f"{total} runs — {s} success / {f} failed  (confidence={conf:.2f})"
            )
        elif self.prior_runs:
            # Fallback for old records not yet in run_index
            n = sum(1 for r in self.prior_runs if r.get("outcome") == "success")
            lines.append(
                f"[civilization] {self.board_id}/{self.test_name}: "
                f"{n}/{len(self.prior_runs)} prior runs succeeded (legacy)"
            )

        # ② relevant_skills
        if self.relevant_skills:
            lines.append(
                f"[civilization] known skills ({len(self.relevant_skills)}):"
            )
            for sk in self.relevant_skills[:3]:
                raw = str(sk.get("raw", ""))[:120]
                conf = sk.get("confidence", 0.5)
                lines.append(f"  skill [{conf:.2f}]: {raw}")

        # ③ likely_pitfalls (avoid_paths)
        if self.avoid_paths:
            lines.append(
                f"[civilization] likely pitfalls ({len(self.avoid_paths)}):"
            )
            for ap in self.avoid_paths[:3]:
                lines.append(f"  pitfall: {str(ap.get('raw', ''))[:100]}")

        # ④ observation_focus — derived from avoid_paths + failure history
        focus: List[str] = []
        for ap in self.avoid_paths[:2]:
            raw = str(ap.get("raw", "")).strip()
            if raw:
                focus.append(raw[:80])
        if stats.get("failure_count", 0) > 0:
            focus.append(
                f"{stats['failure_count']} prior failure(s) on record"
                " — watch for early stage exits"
            )
        if focus:
            lines.append("[civilization] observation focus:")
            for item in focus:
                lines.append(f"  watch: {item}")

        return lines

    def is_empty(self) -> bool:
        return (
            not self.run_stats
            and not self.prior_runs
            and not self.avoid_paths
            and not self.relevant_skills
        )
