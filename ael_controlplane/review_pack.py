from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from ael_controlplane.reporting import default_verification_review_payload, default_verification_review_snapshot


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


def build_review_pack_payload(branch: str, task: Dict, artifacts: Dict) -> Dict:
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

    evidence = {}
    for key in ("plan", "result", "task_log", "run_dir", "plan_report", "plan_results"):
        val = str(artifacts.get(key, "")).strip()
        if val:
            evidence[key] = val

    review = default_verification_review_payload(default_verification_review_snapshot(_repo_root()))
    return {
        "branch": branch,
        "task_title": task_title,
        "task_id": task_id,
        "execution_timestamp": datetime.now().isoformat(timespec="seconds"),
        "execution_mode": execution_mode,
        "summary": str(task.get("summary", "")).strip() or "Autonomous agent execution for requested task.",
        "files_changed": changed or "(no file changes detected)",
        "diff_summary": diffstat or "(no diffstat detected)",
        "evidence": evidence,
        "default_verification_review": review,
        "baseline_readiness_status": str(review.get("baseline_readiness_status", "unavailable")),
        "reproduction_command": f'python3 -m ael submit "{prompt or task_title}"',
        "merge_ready": merge_ready,
    }


def _render_review_pack_markdown(payload: Dict) -> str:
    review = payload.get("default_verification_review", {}) if isinstance(payload.get("default_verification_review"), dict) else {}
    baseline_readiness_status = str(payload.get("baseline_readiness_status") or review.get("baseline_readiness_status") or "unavailable")
    merge_advisory = "baseline readiness aligned" if baseline_readiness_status == "ready" else "warning-only: baseline readiness needs attention"
    lines = [
        f"Branch: {payload.get('branch', '')}",
        f"Task: {payload.get('task_title', '')}",
        f"Task ID: {payload.get('task_id', '')}",
        f"Execution Timestamp: {payload.get('execution_timestamp', '')}",
        f"Execution Mode: {payload.get('execution_mode', '')}",
        "",
        "## Summary",
        str(payload.get("summary", "")).strip() or "Autonomous agent execution for requested task.",
        "",
        "## Files Changed",
        "```text",
        str(payload.get("files_changed", "(no file changes detected)")),
        "```",
        "",
        "## Diff Summary",
        "```text",
        str(payload.get("diff_summary", "(no diffstat detected)")),
        "```",
        "",
        "## Evidence",
    ]
    evidence = payload.get("evidence", {}) if isinstance(payload.get("evidence"), dict) else {}
    for key, val in evidence.items():
        lines.append(f"- {key}: {val}")
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
            "",
            "## Reproduction Instructions",
            "```bash",
            str(payload.get("reproduction_command", "")),
            "```",
            "",
            "## Merge Recommendation",
            f"merge_ready: {payload.get('merge_ready', 'no')}",
            f"baseline_readiness_status: {baseline_readiness_status}",
            f"merge_advisory: {merge_advisory}",
            "",
        ]
    )
    return "\n".join(lines)


def generate_review_pack(branch: str, task: Dict, artifacts: Dict) -> Path:
    reports = _repo_root() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"pr_{_safe_report_name(branch)}.md"
    payload = build_review_pack_payload(branch=branch, task=task, artifacts=artifacts)
    report_path.write_text(_render_review_pack_markdown(payload), encoding="utf-8")
    return report_path
