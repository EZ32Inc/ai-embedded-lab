#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"[REVIEW_PACK_SMOKE] FAIL: {msg}")
    return 2


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    branch = "agent/review-smoke/test"
    task = {
        "title": "review smoke task",
        "task_id": "review_smoke_1",
        "execution_mode": "offline",
        "prompt": "review smoke prompt",
        "merge_ready": "no",
        "summary": "Smoke generation of review pack",
    }
    artifacts = {
        "plan": "runs/smoke/plan.json",
        "result": "runs/smoke/result.json",
        "task_log": "runs/smoke/logs/task.log",
        "run_dir": "runs/smoke",
    }

    # Ensure repository has at least one diff target.
    subprocess.run(["git", "status"], cwd=str(repo), capture_output=True, text=True)

    from ael_controlplane.review_pack import generate_review_pack

    path = generate_review_pack(branch=branch, task=task, artifacts=artifacts)
    if not path.exists():
        return _fail("report file not created")
    text = path.read_text(encoding="utf-8")
    for key in ("Branch:", "Task:", "Task ID:", "Execution Mode:", "## Files Changed", "## Merge Recommendation"):
        if key not in text:
            return _fail(f"missing field: {key}")
    print("[REVIEW_PACK_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
