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


def _extract_task_id(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("task_id:"):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = Path("/tmp/ael_bridge_smoke_queue")
    report_root = Path("/tmp/ael_bridge_smoke_reports")
    up_log = Path("/tmp/ael_bridge_smoke_up.log")

    for p in (queue_root, report_root):
        if p.exists():
            shutil.rmtree(p)
    if up_log.exists():
        up_log.unlink()

    up_cmd = [
        sys.executable,
        "-m",
        "ael",
        "up",
        "--host",
        "127.0.0.1",
        "--port",
        "8844",
        "--queue",
        str(queue_root),
        "--report-root",
        str(report_root),
        "--poll",
        "0.2",
    ]

    with open(up_log, "w", encoding="utf-8") as lf:
        up_proc = subprocess.Popen(up_cmd, cwd=str(repo_root), stdout=lf, stderr=subprocess.STDOUT)

    try:
        healthy = False
        for _ in range(40):
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

        submit = subprocess.run(
            [sys.executable, "-m", "ael", "submit", "run gpio golden test", "--api", "http://127.0.0.1:8844/v1/tasks"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if int(submit.returncode) != 0:
            return _fail(f"NL submit command failed: {submit.stderr or submit.stdout}")
        task_id = _extract_task_id(submit.stdout)
        if not task_id:
            return _fail(f"task_id missing from submit output: {submit.stdout}")
        print("[NL_SUBMIT] OK")

        status_payload = {}
        deadline = time.time() + 12.0
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
        print("[AGENT_SMOKE] OK")
        return 0
    finally:
        if up_proc.poll() is None:
            up_proc.terminate()
            try:
                up_proc.wait(timeout=5)
            except Exception:
                up_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
