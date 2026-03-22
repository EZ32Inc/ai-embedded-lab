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
    - surface a human-readable summary in logs
    """

    board_id: str
    test_name: str

    # Successful / partial past experiences for this board+test combination
    prior_runs: List[dict] = field(default_factory=list)

    # Experiences marked avoid=True (dangerous paths, known failures)
    avoid_paths: List[dict] = field(default_factory=list)

    @property
    def has_prior_success(self) -> bool:
        return any(r.get("outcome") == "success" for r in self.prior_runs)

    @property
    def has_avoid_paths(self) -> bool:
        return len(self.avoid_paths) > 0

    @property
    def prior_success_count(self) -> int:
        return sum(1 for r in self.prior_runs if r.get("outcome") == "success")

    def summary_lines(self) -> List[str]:
        """Human-readable lines for pipeline logging."""
        lines = []
        if not self.prior_runs and not self.avoid_paths:
            lines.append(f"[civilization] no prior experience for {self.board_id}/{self.test_name}")
            return lines

        if self.prior_runs:
            success_n = self.prior_success_count
            total_n = len(self.prior_runs)
            lines.append(
                f"[civilization] {self.board_id}/{self.test_name}: "
                f"{success_n}/{total_n} prior runs succeeded"
            )
            # Surface the most recent successful experience
            successes = [r for r in self.prior_runs if r.get("outcome") == "success"]
            if successes:
                best = max(successes, key=lambda r: r.get("confidence", 0))
                raw_preview = str(best.get("raw", ""))[:120]
                lines.append(f"  best experience: {raw_preview}")

        if self.avoid_paths:
            lines.append(f"[civilization] WARNING: {len(self.avoid_paths)} avoid path(s) known:")
            for ap in self.avoid_paths[:3]:
                lines.append(f"  avoid: {str(ap.get('raw', ''))[:100]}")

        return lines

    def is_empty(self) -> bool:
        return not self.prior_runs and not self.avoid_paths
