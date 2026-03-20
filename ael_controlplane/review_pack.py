from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from ael_controlplane.reporting import default_verification_review_highlights, default_verification_review_snapshot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(args):
    proc = subprocess.run(["git", *args], cwd=str(_repo_root()), capture_output=True, text=True)
    return (proc.stdout or "").strip()


def _safe_report_name(branch: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (branch or "branch"))


def _read_json(path: Path) -> Dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_review_pack(branch: str, task: Dict, artifacts: Dict) -> Path:
    reports = _repo_root() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"pr_{_safe_report_name(branch)}.md"

    task_title = str(task.get("title", "")).strip()
    task_id = str(task.get("task_id", "")).strip()
    execution_mode = str(task.get("execution_mode", "")).strip() or "offline"
    prompt = str(task.get("prompt", "")).strip()
    merge_ready = str(task.get("merge_ready", "no")).strip() or "no"

    base_ref = "main"
    changed = _run_git(["diff", "--name-status", f"{base_ref}...HEAD"])
    diffstat = _run_git(["diff", "--stat", f"{base_ref}...HEAD"])
    if not changed:
        changed = _run_git(["diff", "--name-status", "HEAD~1...HEAD"])
    if not diffstat:
        diffstat = _run_git(["diff", "--stat", "HEAD~1...HEAD"])
    baseline_review = default_verification_review_snapshot(_repo_root())
    baseline_highlights = default_verification_review_highlights(baseline_review)
    schema_review_status = str(baseline_review.get("schema_review_status") or baseline_highlights["schema_review_status"])
    structured_coverage = str(baseline_review.get("structured_coverage") or baseline_highlights["structured_coverage"])
    warning_summary = str(baseline_review.get("warning_summary") or baseline_highlights["warning_summary"])

    lines = [
        f"Branch: {branch}",
        f"Task: {task_title}",
        f"Task ID: {task_id}",
        f"Execution Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"Execution Mode: {execution_mode}",
        "",
        "## Summary",
        str(task.get("summary", "")).strip() or "Autonomous agent execution for requested task.",
        "",
        "## Files Changed",
        "```text",
        changed or "(no file changes detected)",
        "```",
        "",
        "## Diff Summary",
        "```text",
        diffstat or "(no diffstat detected)",
        "```",
        "",
        "## Evidence",
    ]

    for key in ("plan", "result", "task_log", "run_dir", "plan_report", "plan_results"):
        val = str(artifacts.get(key, "")).strip()
        if val:
            lines.append(f"- {key}: {val}")

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
            "",
            "## Reproduction Instructions",
            "```bash",
            f'python3 -m ael submit "{prompt or task_title}"',
            "```",
            "",
            "## Merge Recommendation",
            f"merge_ready: {merge_ready}",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
