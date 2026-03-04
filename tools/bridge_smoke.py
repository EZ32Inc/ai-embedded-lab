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
    print(f"[BRIDGE_SMOKE] FAIL: {msg}")
    return 2


def _http_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url=url, data=data, method=method, headers=headers)
    with request.urlopen(req, timeout=5) as resp:
        body = (resp.read() or b"{}").decode("utf-8")
        out = json.loads(body) if body else {}
        return int(resp.status), out if isinstance(out, dict) else {}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_bridge_smoke_queue")
    report_root = Path("/tmp/ael_bridge_smoke_reports")
    bridge_log = Path("/tmp/ael_bridge_smoke_bridge.log")
    agent_log = Path("/tmp/ael_bridge_smoke_agent.log")

    for p in (queue_root, report_root):
        if p.exists():
            shutil.rmtree(p)
    for p in (bridge_log, agent_log):
        if p.exists():
            p.unlink()

    bridge_cmd = [
        sys.executable,
        "-m",
        "ael",
        "bridge",
        "--host",
        "127.0.0.1",
        "--port",
        "8844",
        "--queue",
        str(queue_root),
    ]
    agent_cmd = [
        sys.executable,
        "-m",
        "ael.agent",
        "--queue",
        str(queue_root),
        "--report-root",
        str(report_root),
        "--poll",
        "0.2",
    ]

    with open(bridge_log, "w", encoding="utf-8") as bf:
        bridge_proc = subprocess.Popen(bridge_cmd, cwd=str(repo_root), stdout=bf, stderr=subprocess.STDOUT)
    with open(agent_log, "w", encoding="utf-8") as af:
        agent_proc = subprocess.Popen(agent_cmd, cwd=str(repo_root), stdout=af, stderr=subprocess.STDOUT)

    try:
        healthy = False
        for _ in range(30):
            try:
                code, health = _http_json("GET", "http://127.0.0.1:8844/health")
                if code == 200 and bool(health.get("ok")):
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not healthy:
            return _fail("bridge health check failed")

        code, created = _http_json(
            "POST",
            "http://127.0.0.1:8844/v1/tasks",
            {
                "title": "bridge_smoke",
                "kind": "noop",
                "payload": {},
                "priority": 0,
            },
        )
        if code != 200 or not bool(created.get("ok", False)):
            return _fail(f"task submit failed: {created}")
        task_id = str(created.get("task_id", "")).strip()
        if not task_id:
            return _fail("task_id missing from submit response")

        status_payload = {}
        deadline = time.time() + 10.0
        while time.time() < deadline:
            code, status_payload = _http_json("GET", f"http://127.0.0.1:8844/v1/tasks/{task_id}")
            if code == 200 and status_payload.get("state") in ("done", "failed"):
                break
            time.sleep(0.2)
        if status_payload.get("state") != "done":
            return _fail(f"task did not finish as done: {status_payload}")

        code, result = _http_json("GET", f"http://127.0.0.1:8844/v1/tasks/{task_id}/result")
        if code != 200:
            return _fail(f"result fetch failed: {result}")
        if not bool(result.get("ok", False)):
            return _fail(f"result ok=false: {result}")

        print("[BRIDGE_SMOKE] OK")
        return 0
    finally:
        for proc in (agent_proc, bridge_proc):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
