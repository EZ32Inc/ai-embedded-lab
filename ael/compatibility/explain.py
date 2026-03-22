"""Human-readable explanations for compatibility results.

Used by doctor output, CLI, and future UI integrations.
"""

from __future__ import annotations

from ael.compatibility.model import CompatibilityResult, ExecutionPlan


def explain_compatibility(result: CompatibilityResult) -> str:
    """Return a concise human-readable description of a CompatibilityResult."""
    lines: list[str] = []
    status = "COMPATIBLE" if result.compatible else "NOT COMPATIBLE"
    lines.append(f"[{status}] score={result.score}/100")
    for r in result.reasons:
        lines.append(f"  {r}")
    for m in result.missing_capabilities:
        lines.append(f"  missing: {m}")
    for w in result.warnings:
        lines.append(f"  warning: {w}")
    return "\n".join(lines)


def explain_plan(plan: ExecutionPlan) -> str:
    """Return a concise human-readable description of an ExecutionPlan."""
    lines: list[str] = []
    status = "EXECUTABLE" if plan.executable else "NOT EXECUTABLE"
    lines.append(f"[{status}]")
    for r in plan.reasons:
        lines.append(f"  {r}")
    if plan.selected_instruments:
        lines.append(f"  instruments: {', '.join(plan.selected_instruments)}")
    for m in plan.missing_requirements:
        lines.append(f"  missing: {m}")
    for w in plan.warnings:
        lines.append(f"  warning: {w}")
    for s in plan.suggested_alternatives:
        lines.append(f"  suggestion: {s}")
    return "\n".join(lines)
