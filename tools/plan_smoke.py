#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request


def _fail(msg: str) -> int:
    print(f"[PLAN_SMOKE] FAIL: {msg}")
    return 2


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _http_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url=url, method=method, data=data, headers=headers)
    with request.urlopen(req, timeout=5) as resp:
        body = (resp.read() or b"{}").decode("utf-8")
        payload = json.loads(body) if body else {}
        return int(resp.status), payload if isinstance(payload, dict) else {}


def _extract_task_id(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("task_id:"):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_plan_smoke_queue")
    report_root = Path("/tmp/ael_plan_smoke_reports")
    bridge_log = Path("/tmp/ael_plan_smoke_bridge.log")
    agent_log = Path("/tmp/ael_plan_smoke_agent.log")
    port = _pick_free_port()
    api_base = f"http://127.0.0.1:{port}"

    for p in (queue_root, report_root):
        if p.exists():
            shutil.rmtree(p)
    for p in (bridge_log, agent_log):
        if p.exists():
            p.unlink()

    bridge_cmd = [
        sys.executable,
        "-m",
        "ael_controlplane.bridge_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--queue",
        str(queue_root),
    ]
    agent_cmd = [
        sys.executable,
        "-m",
        "ael_controlplane.agent",
        "--queue",
        str(queue_root),
        "--report-root",
        str(report_root),
        "--poll",
        "0.2",
    ]
    with open(bridge_log, "w", encoding="utf-8") as blf:
        bridge_proc = subprocess.Popen(bridge_cmd, cwd=str(repo_root), stdout=blf, stderr=subprocess.STDOUT)
    with open(agent_log, "w", encoding="utf-8") as alf:
        agent_proc = subprocess.Popen(agent_cmd, cwd=str(repo_root), stdout=alf, stderr=subprocess.STDOUT)

    try:
        healthy = False
        for _ in range(40):
            try:
                code, payload = _http_json("GET", f"{api_base}/health")
                if code == 200 and bool(payload.get("ok", False)):
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not healthy:
            return _fail("bridge health check failed")

        code, submit_payload = _http_json(
            "POST",
            f"{api_base}/v1/tasks",
            {
                "title": "plan smoke",
                "kind": "plan",
                "payload": {"prompt": "develop gpio golden test for stm32f103"},
                "priority": 0,
            },
        )
        if code != 200 or not bool(submit_payload.get("ok", False)):
            return _fail(f"submit failed: {submit_payload}")
        task_id = str(submit_payload.get("task_id", "")).strip()
        if not task_id:
            return _fail(f"task_id missing from submit payload: {submit_payload}")

        state = ""
        status_payload = {}
        deadline = time.time() + 20.0
        while time.time() < deadline:
            code, status_payload = _http_json("GET", f"{api_base}/v1/tasks/{task_id}")
            if code == 200:
                state = str(status_payload.get("state", ""))
                if state in ("done", "failed"):
                    break
            time.sleep(0.2)
        if state != "done":
            return _fail(f"plan task not done: {status_payload}")

        code, result = _http_json("GET", f"{api_base}/v1/tasks/{task_id}/result")
        if code != 200 or not bool(result.get("ok", False)):
            return _fail(f"result not ok: {result}")

        run_dir = Path(str(result.get("run_dir", "")))
        if not run_dir.exists():
            return _fail(f"run_dir missing: {run_dir}")
        if not (run_dir / "plan.json").exists():
            return _fail("plan.json missing")
        if not (run_dir / "artifacts" / "plan_results.json").exists():
            return _fail("plan_results.json missing")
        if not (run_dir / "tasks").exists():
            return _fail("tasks/ directory missing")

        report_path = report_root / f"plan_{task_id}.md"
        if not report_path.exists():
            return _fail(f"plan report missing: {report_path}")

        print("[PLAN_SMOKE] OK")
        return 0
    finally:
        if bridge_proc.poll() is None:
            bridge_proc.terminate()
            try:
                bridge_proc.wait(timeout=5)
            except Exception:
                bridge_proc.kill()
        if agent_proc.poll() is None:
            agent_proc.terminate()
            try:
                agent_proc.wait(timeout=5)
            except Exception:
                agent_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
