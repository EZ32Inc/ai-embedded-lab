#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import request


def _fail(msg: str) -> int:
    print(f"[TASK_API_SMOKE] FAIL: {msg}")
    return 2


def _get_json(url: str) -> dict:
    with request.urlopen(url, timeout=5) as resp:
        body = (resp.read() or b"{}").decode("utf-8")
        payload = json.loads(body) if body else {}
        return payload if isinstance(payload, dict) else {}


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=5) as resp:
        body = (resp.read() or b"{}").decode("utf-8")
        out = json.loads(body) if body else {}
        return int(resp.status), out if isinstance(out, dict) else {}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_task_api_smoke_queue")
    report_root = Path("/tmp/ael_task_api_smoke_reports")
    api_log = Path("/tmp/ael_task_api_smoke.log")

    if queue_root.exists():
        shutil.rmtree(queue_root)
    if report_root.exists():
        shutil.rmtree(report_root)
    if api_log.exists():
        api_log.unlink()

    cmd = [
        sys.executable,
        "-m",
        "ael_controlplane.task_api",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--queue",
        str(queue_root),
        "--report-root",
        str(report_root),
    ]

    with open(api_log, "w", encoding="utf-8") as logf:
        api_proc = subprocess.Popen(cmd, cwd=str(repo_root), stdout=logf, stderr=subprocess.STDOUT)

    try:
        health = {}
        for _ in range(30):
            try:
                health = _get_json("http://127.0.0.1:8765/health")
                break
            except Exception:
                time.sleep(0.2)
        if not health or not bool(health.get("ok")):
            return _fail("health endpoint did not return ok=true")

        status, accepted = _post_json(
            "http://127.0.0.1:8765/v1/tasks",
            {
                "task_id": "task_api_smoke_1",
                "description": "task api smoke",
                "plan_file": "docs/night_tasks_agent_v0_3.md",
                "priority": "normal",
            },
        )
        if status != 200 or not bool(accepted.get("accepted")):
            return _fail(f"submit failed: status={status} payload={accepted}")

        task_path = queue_root / "inbox" / "task_api_smoke_1.json"
        if not task_path.exists():
            return _fail("submitted task file missing in inbox")

        run_agent = subprocess.run(
            [sys.executable, "-m", "ael_controlplane.agent", "--once", "--queue", str(queue_root), "--report-root", str(report_root)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if int(run_agent.returncode) != 0:
            return _fail(f"agent exited with {run_agent.returncode}: {run_agent.stderr or run_agent.stdout}")

        done_task = queue_root / "done" / "task_api_smoke_1.json"
        done_state = queue_root / "done" / "task_api_smoke_1.state.json"
        if not done_task.exists():
            return _fail("task was not moved to done")
        if not done_state.exists():
            return _fail("done state not found")

        payload = json.loads(done_state.read_text(encoding="utf-8"))
        if not bool(payload.get("ok", False)):
            return _fail(f"task state not ok: {payload}")

        log_path = report_root / "task_log.md"
        if not log_path.exists():
            return _fail("reports/task_log.md was not created")

        print("[TASK_API_SMOKE] OK")
        return 0
    finally:
        if api_proc.poll() is None:
            api_proc.terminate()
            try:
                api_proc.wait(timeout=5)
            except Exception:
                api_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
