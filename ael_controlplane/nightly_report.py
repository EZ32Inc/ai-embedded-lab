from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ael_controlplane.reporting import default_verification_review_payload, default_verification_review_snapshot


def build_nightly_report_payload(date_str: str, summary: dict) -> Dict:
    plans: List[Dict] = summary.get("plans", []) if isinstance(summary.get("plans"), list) else []
    baseline_review = summary.get("default_verification_review") if isinstance(summary.get("default_verification_review"), dict) else default_verification_review_snapshot(Path(__file__).resolve().parents[1])
    review = default_verification_review_payload(baseline_review)
    baseline_readiness_status = str(summary.get("baseline_readiness_status") or review.get("baseline_readiness_status") or "unavailable")
    failures: List[Dict] = []
    for p in plans:
        if str(p.get("status", "")).upper() in ("FAIL", "FAILED"):
            failures.append(
                {
                    "title": str(p.get("title", "")),
                    "task_id": str(p.get("task_id", "")),
                    "error": str(p.get("error_summary", "")),
                    "human_action": "inspect run_dir logs and artifacts.",
                    "suggested_next": "retry with narrower prompt or dry-run.",
                }
            )
    merge_rows: List[Dict] = []
    for p in plans:
        merge_rows.append(
            {
                "branch": str(p.get("branch", "")),
                "task": str(p.get("title", "")),
                "status": str(p.get("status", "")),
                "execution_mode": str(p.get("execution_mode", "")),
                "tests": str(p.get("tests", "")),
                "merge_ready": str(p.get("merge_ready", "")),
            }
        )
    changes: List[Dict] = []
    for p in plans:
        commit = str(p.get("commit", "")).strip()
        if not commit:
            continue
        changes.append(
            {
                "commit": commit,
                "title": str(p.get("title", "")),
                "diffstat_lines": [line for line in str(p.get("diffstat", "")).splitlines() if line.strip()],
            }
        )
    return {
        "date": date_str,
        "started_at": str(summary.get("started_at", "")),
        "finished_at": str(summary.get("finished_at", "")),
        "overall_ok": bool(summary.get("ok", False)),
        "plans": plans,
        "failures": failures,
        "default_verification_review": review,
        "baseline_readiness_status": baseline_readiness_status,
        "merge_readiness": merge_rows,
        "changes": changes,
    }


def _render_nightly_report_markdown(payload: Dict) -> str:
    plans = payload.get("plans", []) if isinstance(payload.get("plans"), list) else []
    review = payload.get("default_verification_review", {}) if isinstance(payload.get("default_verification_review"), dict) else {}
    baseline_readiness_status = str(payload.get("baseline_readiness_status") or review.get("baseline_readiness_status") or "unavailable")
    merge_advisory = "baseline readiness aligned" if baseline_readiness_status == "ready" else "warning-only: baseline readiness needs attention"
    lines = [
        f"# AEL Nightly Report — {payload.get('date', '')}",
        f"- Started: {payload.get('started_at', '')}",
        f"- Finished: {payload.get('finished_at', '')}",
        f"- Overall: {'OK' if bool(payload.get('overall_ok', False)) else 'FAILED'}",
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
    failures = payload.get("failures", []) if isinstance(payload.get("failures"), list) else []
    if not failures:
        lines.append("- None")
    for failure in failures:
        lines.extend(
            [
                f"### {failure.get('title','')} ({failure.get('task_id','')})",
                f"- Error: {failure.get('error','')}",
                f"- Human action: {failure.get('human_action','')}",
                f"- Suggested next: {failure.get('suggested_next','')}",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## Default Verification Review",
            f"- schema_review_status: {review.get('schema_review_status', 'unavailable')}",
            f"- structured_coverage: {review.get('structured_coverage', 'unavailable')}",
            f"- warning_summary: {review.get('warning_summary', 'unavailable')}",
            "```text",
            str(review.get("text") or review.get("error") or "(unavailable)"),
            "```",
        ]
    )
    lines.extend(
        [
            "",
            "## Merge Readiness",
            f"- baseline_readiness_status: {baseline_readiness_status}",
            f"- merge_advisory: {merge_advisory}",
            "| Branch | Task | Status | Execution Mode | Tests | Merge Ready |",
            "|------|------|------|------|------|------|",
        ]
    )
    merge_rows = payload.get("merge_readiness", []) if isinstance(payload.get("merge_readiness"), list) else []
    for row in merge_rows:
        lines.append(
            f"| {row.get('branch','')} | {row.get('task','')} | {row.get('status','')} | {row.get('execution_mode','')} | {row.get('tests','')} | {row.get('merge_ready','')} |"
        )
    lines.extend(["", "## Changes"])
    changes = payload.get("changes", []) if isinstance(payload.get("changes"), list) else []
    if not changes:
        lines.append("- No commits produced.")
    for change in changes:
        lines.append(f"- {change.get('commit','')} {change.get('title', '')}")
        for line in change.get("diffstat_lines", []):
            lines.append(f"  - {line}")
    return "\n".join(lines) + "\n"


def write_nightly_report(date_str: str, summary: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_nightly_report_payload(date_str, summary)
    path.write_text(_render_nightly_report_markdown(payload), encoding="utf-8")
    return path
