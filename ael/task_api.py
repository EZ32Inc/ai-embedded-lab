from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

from ael.queue import ensure_queue_layout


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_task_id(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = text.strip("._-")
    return text or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _append_task_log(report_root: Path, task_id: str, plan_file: str, source: str = "task_api") -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    log_path = report_root / "task_log.md"
    lines = [
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        "",
        "TASK ACCEPTED",
        f"task_id: {task_id}",
        f"plan: {plan_file}",
        f"source: {source}",
        "",
    ]
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _validate_submit(body: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(body, dict):
        return False, "request body must be a JSON object"
    plan_file = body.get("plan_file")
    if not isinstance(plan_file, str) or not plan_file.strip():
        return False, "plan_file is required"
    return True, ""


def _normalize_task(body: Dict[str, Any]) -> Dict[str, Any]:
    task_id = _safe_task_id(str(body.get("task_id", "")))
    priority = body.get("priority", "normal")
    if not isinstance(priority, str):
        priority = str(priority)
    task = {
        "task_id": task_id,
        "description": str(body.get("description", "")).strip(),
        "plan_file": str(body.get("plan_file", "")).strip(),
        "created_by": str(body.get("created_by", "chatgpt")).strip() or "chatgpt",
        "priority": priority.strip() or "normal",
        "timestamp": str(body.get("timestamp", "")).strip() or _now_iso(),
    }
    return task


def _make_handler(queue_root: Path, report_root: Path):
    ensure_queue_layout(queue_root)

    class TaskApiHandler(BaseHTTPRequestHandler):
        server_version = "ael-task-api/0.3"

        def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
            encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self._send_json(404, {"ok": False, "error": "not found"})
                return
            self._send_json(200, {"ok": True, "service": "ael-task-api", "version": "0.3"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/tasks":
                self._send_json(404, {"ok": False, "error": "not found"})
                return

            try:
                content_len = int(self.headers.get("Content-Length", "0"))
            except Exception:
                content_len = 0
            raw = self.rfile.read(content_len)

            try:
                body = json.loads(raw.decode("utf-8") if raw else "{}")
            except Exception:
                self._send_json(400, {"ok": False, "error": "invalid JSON"})
                return

            ok, err = _validate_submit(body)
            if not ok:
                self._send_json(400, {"ok": False, "error": err})
                return

            task = _normalize_task(body)
            task_id = task["task_id"]
            inbox = ensure_queue_layout(queue_root)["inbox"]
            task_path = inbox / f"{task_id}.json"
            if task_path.exists():
                self._send_json(409, {"ok": False, "error": "task_id already exists", "task_id": task_id})
                return

            task_path.write_text(json.dumps(task, indent=2, sort_keys=True), encoding="utf-8")
            _append_task_log(report_root, task_id=task_id, plan_file=task["plan_file"])
            self._send_json(200, {"accepted": True, "task_id": task_id})

    return TaskApiHandler


def run_server(host: str = "127.0.0.1", port: int = 8765, queue_root: str = "queue", report_root: str = "reports") -> int:
    queue_path = Path(queue_root).resolve()
    report_path = Path(report_root).resolve()
    handler = _make_handler(queue_path, report_path)
    server = ThreadingHTTPServer((host, int(port)), handler)
    print(f"Task API: listening on http://{host}:{port}")
    print(f"Task API: queue={queue_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ael.task_api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--queue", default="queue")
    parser.add_argument("--report-root", default="reports")
    args = parser.parse_args()
    return run_server(host=args.host, port=args.port, queue_root=args.queue, report_root=args.report_root)


if __name__ == "__main__":
    raise SystemExit(main())
