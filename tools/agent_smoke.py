#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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
    gates_path = Path("/tmp/ael_agent_smoke_gates.json")
    report_root = Path("/tmp/ael_agent_smoke_reports")

    if queue_root.exists():
        shutil.rmtree(queue_root)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    if gates_path.exists():
        gates_path.unlink()
    if report_root.exists():
        shutil.rmtree(report_root)
    (queue_root / "inbox").mkdir(parents=True, exist_ok=True)

    original_branch_res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if original_branch_res.returncode != 0:
        return _fail("failed to resolve current git branch")
    original_branch = (original_branch_res.stdout or "").strip()
    smoke_branch = f"agent/{date.today().isoformat()}/task-0001-agent-smoke"
    if original_branch == smoke_branch:
        fallback = subprocess.run(
            ["git", "checkout", "master"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if fallback.returncode != 0:
            fallback = subprocess.run(
                ["git", "checkout", "main"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
        if fallback.returncode != 0:
            return _fail("failed to checkout a non-smoke branch for cleanup")
        original_branch = (subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        ).stdout or "").strip() or original_branch
    subprocess.run(["git", "branch", "-D", smoke_branch], cwd=str(repo_root), capture_output=True, text=True)

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
            "test_config": "tests/plans/none.json",
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
    gates_path.write_text(
        json.dumps(
            {
                "commands": [
                    "python3 -m py_compile ael_controlplane/agent.py ael_controlplane/queue.py ael_controlplane/reporting.py",
                    "python3 tools/runner_smoke.py",
                    "python3 -m py_compile ael/runner.py",
                    "python3 -m py_compile tools/agent_smoke.py",
                ]
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "ael_controlplane.agent",
        "--once",
        "--branch-worker",
        "--no-push",
        "--queue",
        str(queue_root),
        "--gates",
        str(gates_path),
        "--report-root",
        str(report_root),
    ]
    env = dict(**os.environ, AEL_AGENT_ALLOW_DIRTY="1")
    p = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, env=env)
    if p.returncode != 0:
        return _fail(f"agent exit code {p.returncode}\nstdout={p.stdout}\nstderr={p.stderr}")

    done_task = queue_root / "done" / task_name
    done_state = queue_root / "done" / task_name.replace(".json", ".state.json")
    if not done_task.exists():
        return _fail("task was not moved to queue/done")
    if not done_state.exists():
        return _fail("done state json was not created")
    try:
        state_payload = json.loads(done_state.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail(f"failed to parse done state: {exc}")
    branch_name = str(state_payload.get("branch_name", "")).strip()
    base_commit = str(state_payload.get("base_commit", "")).strip()
    if not branch_name:
        return _fail("branch_name missing in task state")
    if not base_commit:
        return _fail("base_commit missing in task state")

    branch_check = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if branch_check.returncode != 0:
        return _fail("created task branch not found in repository")

    subprocess.run(["git", "checkout", original_branch], cwd=str(repo_root), capture_output=True, text=True)
    subprocess.run(["git", "branch", "-D", branch_name], cwd=str(repo_root), capture_output=True, text=True)

    if not (run_dir / "artifacts" / "run_plan.json").exists():
        return _fail("run_plan artifact missing")
    if not (run_dir / "artifacts" / "result.json").exists():
        return _fail("result artifact missing")

    nightly = report_root / f"nightly_{date.today().isoformat()}.md"
    if not nightly.exists():
        return _fail("nightly report not found")

    print("[AGENT_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
