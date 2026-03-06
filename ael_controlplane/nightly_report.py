from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def write_nightly_report(date_str: str, summary: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plans: List[Dict] = summary.get("plans", []) if isinstance(summary.get("plans"), list) else []
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
