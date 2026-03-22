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
    """

    board_id: str
    test_name: str

    # EE records for this board+test (excluding avoid paths)
    prior_runs: List[dict] = field(default_factory=list)

    # Experiences marked avoid=True (dangerous paths, known failures)
    avoid_paths: List[dict] = field(default_factory=list)

    # Aggregated statistics from run_index (success_count, failure_count, confidence, last_seen)
    run_stats: dict = field(default_factory=dict)

    @property
    def has_prior_success(self) -> bool:
        return self.run_stats.get("success_count", 0) > 0 or any(
            r.get("outcome") == "success" for r in self.prior_runs
        )

    @property
    def has_avoid_paths(self) -> bool:
        return len(self.avoid_paths) > 0

    def summary_lines(self) -> List[str]:
        """Human-readable lines for pipeline logging."""
        lines = []
        stats = self.run_stats

        if not stats and not self.prior_runs and not self.avoid_paths:
            lines.append(
                f"[civilization] no prior experience for {self.board_id}/{self.test_name}"
            )
            return lines

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

        if self.avoid_paths:
            lines.append(
                f"[civilization] WARNING: {len(self.avoid_paths)} avoid path(s) known:"
            )
            for ap in self.avoid_paths[:3]:
                lines.append(f"  avoid: {str(ap.get('raw', ''))[:100]}")

        return lines

    def is_empty(self) -> bool:
        return not self.run_stats and not self.prior_runs and not self.avoid_paths
