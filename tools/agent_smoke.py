#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"[AGENT_SMOKE] FAIL: {msg}")
    return 2


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_agent_smoke_queue")
    run_dir = Path("/tmp/ael_agent_smoke_run")

    if queue_root.exists():
        shutil.rmtree(queue_root)
    if run_dir.exists():
        shutil.rmtree(run_dir)

    (queue_root / "inbox").mkdir(parents=True, exist_ok=True)

    task_id = "agent-smoke"
    task_name = f"2099-01-01_00-00-00_{task_id}.json"
    task_path = queue_root / "inbox" / task_name

    plan = {
        "version": "runplan/0.1",
        "plan_id": "agent-smoke-plan",
        "created_at": "2026-03-04T00:00:00Z",
        "inputs": {
            "board_id": "smoke",
            "test_id": "agent_smoke",
        },
        "selected": {
            "test_config": "tests/none.json",
        },
        "context": {
            "workspace_dir": str(repo_root),
            "run_root": str(repo_root / "runs"),
            "artifact_root": str(run_dir / "artifacts"),
            "log_root": str(run_dir / "logs"),
        },
        "steps": [
            {
                "name": "check_smoke",
                "type": "check.noop",
                "inputs": {
                    "note": "agent-smoke",
                    "out_json": str(run_dir / "artifacts" / "smoke_noop.json"),
                },
            }
        ],
        "recovery_policy": {
            "enabled": False,
        },
        "meta": {
            "run_dir": str(run_dir),
        },
    }

    task = {
        "task_version": "agenttask/0.1",
        "task_id": task_id,
        "created_at": "2026-03-04T00:00:00Z",
        "priority": 10,
        "plan": plan,
        "validate": {
            "pre": [],
            "post": [],
        },
    }

    task_path.write_text(json.dumps(task, indent=2, sort_keys=True), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "ael.agent",
        "--once",
        "--queue",
        str(queue_root),
    ]
    p = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    if p.returncode != 0:
        return _fail(f"agent exit code {p.returncode}\nstdout={p.stdout}\nstderr={p.stderr}")

    done_task = queue_root / "done" / task_name
    done_state = queue_root / "done" / task_name.replace(".json", ".state.json")
    if not done_task.exists():
        return _fail("task was not moved to queue/done")
    if not done_state.exists():
        return _fail("done state json was not created")

    if not (run_dir / "artifacts" / "run_plan.json").exists():
        return _fail("run_plan artifact missing")
    if not (run_dir / "artifacts" / "result.json").exists():
        return _fail("result artifact missing")

    nightly = repo_root / "reports" / f"nightly_{date.today().isoformat()}.md"
    if not nightly.exists():
        return _fail("nightly report not found")

    print("[AGENT_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
