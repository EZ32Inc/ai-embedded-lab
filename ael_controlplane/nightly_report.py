from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ael_controlplane.reporting import default_verification_review_highlights, default_verification_review_snapshot


def write_nightly_report(date_str: str, summary: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plans: List[Dict] = summary.get("plans", []) if isinstance(summary.get("plans"), list) else []
    baseline_review = summary.get("default_verification_review") if isinstance(summary.get("default_verification_review"), dict) else default_verification_review_snapshot(Path(__file__).resolve().parents[1])
    baseline_highlights = default_verification_review_highlights(baseline_review)
    schema_review_status = str(baseline_review.get("schema_review_status") or baseline_highlights["schema_review_status"])
    structured_coverage = str(baseline_review.get("structured_coverage") or baseline_highlights["structured_coverage"])
    warning_summary = str(baseline_review.get("warning_summary") or baseline_highlights["warning_summary"])
    lines = [
        f"# AEL Nightly Report — {date_str}",
        f"- Started: {summary.get('started_at', '')}",
        f"- Finished: {summary.get('finished_at', '')}",
        f"- Overall: {'OK' if bool(summary.get('ok', False)) else 'FAILED'}",
        "",
        "## Plans",
        "| # | Title | Task ID | Branch | Status | Commit | Run Dir |",
        "|---|-------|---------|--------|--------|--------|--------|",
    ]
    for i, p in enumerate(plans, start=1):
        lines.append(
            f"| {i} | {p.get('title','')} | {p.get('task_id','')} | {p.get('branch','')} | {p.get('status','')} | {p.get('commit','')} | {p.get('run_dir','')} |"
        )
    lines.extend(["", "## Failures"])
    fail_any = False
    for p in plans:
        if str(p.get("status", "")).upper() in ("FAIL", "FAILED"):
            fail_any = True
            lines.extend(
                [
                    f"### {p.get('title','')} ({p.get('task_id','')})",
                    f"- Error: {p.get('error_summary','')}",
                    "- Human action: inspect run_dir logs and artifacts.",
                    "- Suggested next: retry with narrower prompt or dry-run.",
                    "",
                ]
            )
    if not fail_any:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Default Verification Review",
            f"- schema_review_status: {schema_review_status}",
            f"- structured_coverage: {structured_coverage}",
            f"- warning_summary: {warning_summary}",
            "```text",
            str(baseline_review.get("text") or baseline_review.get("error") or "(unavailable)"),
            "```",
        ]
    )
    lines.extend(
        [
            "",
            "## Merge Readiness",
            "| Branch | Task | Status | Execution Mode | Tests | Merge Ready |",
            "|------|------|------|------|------|------|",
        ]
    )
    for p in plans:
        lines.append(
            f"| {p.get('branch','')} | {p.get('title','')} | {p.get('status','')} | "
            f"{p.get('execution_mode','')} | {p.get('tests','')} | {p.get('merge_ready','')} |"
        )
    lines.extend(["", "## Changes"])
    changes = False
    for p in plans:
        commit = str(p.get("commit", "")).strip()
        if not commit:
            continue
        changes = True
        lines.append(f"- {commit} {p.get('title', '')}")
        stat = str(p.get("diffstat", "")).strip()
        for line in stat.splitlines():
            lines.append(f"  - {line}")
    if not changes:
        lines.append("- No commits produced.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
