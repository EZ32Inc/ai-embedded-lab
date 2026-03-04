#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"[NIGHTLY_SMOKE] FAIL: {msg}")
    return 2


def _run(cmd, cwd: Path):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_nightly_smoke_queue")
    report_root = Path("/tmp/ael_nightly_smoke_reports")
    for p in (queue_root, report_root):
        if p.exists():
            shutil.rmtree(p)
    (queue_root / "inbox").mkdir(parents=True, exist_ok=True)

    task = {
        "task_id": "nightly_smoke_plan_1",
        "title": "nightly smoke plan",
        "kind": "plan",
        "payload": {"prompt": "Create a no-op plan and execute check.noop"},
    }
    (queue_root / "inbox" / "nightly_smoke_plan_1.json").write_text(json.dumps(task, indent=2), encoding="utf-8")

    base = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if base.returncode != 0:
        return _fail("cannot resolve current branch")
    original_branch = (base.stdout or "").strip()
    smoke_branch = "agent/nightly-smoke/base"
    _run(["git", "checkout", "-B", smoke_branch], cwd=repo)
    base_branch = smoke_branch

    dry = _run(
        [
            sys.executable,
            "-m",
            "ael",
            "nightly",
            "--queue",
            str(queue_root),
            "--report-root",
            str(report_root),
            "--allow-on-master",
            "--dry-run",
            "--max-plans",
            "1",
        ],
        cwd=repo,
    )
    if dry.returncode != 0:
        return _fail(f"dry-run failed: {dry.stderr or dry.stdout}")

    day = datetime.now().strftime("%Y-%m-%d")
    report = report_root / f"nightly_{day}.md"
    if not report.exists():
        return _fail("dry-run report missing")

    (queue_root / "inbox").mkdir(parents=True, exist_ok=True)
    (queue_root / "inbox" / "nightly_smoke_plan_1.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
    real = _run(
        [
            sys.executable,
            "-m",
            "ael",
            "nightly",
            "--queue",
            str(queue_root),
            "--report-root",
            str(report_root),
            "--allow-on-master",
            "--max-plans",
            "1",
        ],
        cwd=repo,
    )
    if real.returncode != 0:
        return _fail(f"real run failed: {real.stderr or real.stdout}")
    if not report.exists():
        return _fail("real-run report missing")

    after = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if after.returncode != 0 or (after.stdout or "").strip() != base_branch:
        return _fail(f"working branch not restored (expected={base_branch}, got={(after.stdout or '').strip()})")

    branches = _run(["git", "branch", "--list", "agent/*"], cwd=repo)
    if branches.returncode != 0 or not (branches.stdout or "").strip():
        return _fail("no nightly branch created")

    _run(["git", "checkout", original_branch], cwd=repo)

    print("[NIGHTLY_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
