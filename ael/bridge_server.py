from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote

from ael.bridge_task import build_task, task_filename, validate_submit_request
from ael.queue import ensure_queue_layout


def _json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _state_file(task_path: Path) -> Path:
    return task_path.with_suffix(".state.json")


def _find_task_in_state(queue_root: Path, state: str, task_id: str) -> Optional[Path]:
    state_dir = queue_root / state
    if not state_dir.exists():
        return None
    direct = list(state_dir.glob(f"{task_id}__*.json"))
    for p in sorted(direct):
        if p.name.endswith(".state.json"):
            continue
        return p
    for p in sorted(state_dir.glob("*.json")):
        if p.name.endswith(".state.json"):
            continue
        data = _read_json(p)
        if not data:
            continue
        if str(data.get("task_id", "")).strip() == task_id:
            return p
    return None


def _find_task(queue_root: Path, task_id: str) -> Tuple[Optional[str], Optional[Path]]:
    for state in ("running", "inbox", "done", "failed"):
        path = _find_task_in_state(queue_root, state, task_id)
        if path:
            return state, path
    return None, None


def _auth_enabled() -> bool:
    return bool(os.environ.get("AEL_BRIDGE_TOKEN", "").strip())


def _auth_ok(headers: Any) -> bool:
    expected = os.environ.get("AEL_BRIDGE_TOKEN", "").strip()
    if not expected:
        return True
    got = str(headers.get("X-AEL-Token", "")).strip()
    return got == expected


def _safe_artifact_path(run_dir: Path, relpath: str) -> Optional[Path]:
    rel = Path(unquote(relpath))
    if rel.is_absolute():
        return None
    candidate = (run_dir / rel).resolve()
    try:
        base = run_dir.resolve()
    except Exception:
        return None
    if not str(candidate).startswith(str(base)):
        return None
    return candidate


def _write_task_atomic(inbox_dir: Path, payload: Dict[str, Any], filename: str) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    target = inbox_dir / filename
    if target.exists():
        raise FileExistsError(str(target))
    data = _json_bytes(payload)
    tmp_name = str(inbox_dir / f".tmp_bridge_{os.getpid()}_{int(time.time() * 1000)}.tmp")
    try:
        with open(tmp_name, "wb") as tmpf:
            tmpf.write(data)
            tmpf.flush()
            os.fsync(tmpf.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
    return target


def _make_handler(queue_root: Path):
    ensure_queue_layout(queue_root)

    class BridgeHandler(BaseHTTPRequestHandler):
        server_version = "ael-bridge/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
            data = _json_bytes(payload)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _require_auth(self) -> bool:
            if self.path == "/health":
                return True
            if _auth_ok(self.headers):
                return True
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return False

        def do_GET(self) -> None:  # noqa: N802
            if not self._require_auth():
                return

            if self.path == "/health":
                self._send_json(200, {"ok": True, "version": "bridge/0.1"})
                return

            if self.path.startswith("/v1/tasks/") and self.path.endswith("/stream"):
                self._handle_stream()
                return

            if self.path.startswith("/v1/tasks/") and "/artifacts/" in self.path:
                self._handle_artifact()
                return

            if self.path.startswith("/v1/tasks/") and self.path.endswith("/result"):
                self._handle_result()
                return

            if self.path.startswith("/v1/tasks/"):
                self._handle_status()
                return

            self._send_json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if not self._require_auth():
                return
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

            ok, err = validate_submit_request(body if isinstance(body, dict) else {})
            if not ok:
                self._send_json(400, {"ok": False, "error": err})
                return

            priority = body.get("priority", 0)
            try:
                priority = int(priority)
            except Exception:
                priority = 0

            task = build_task(
                title=str(body.get("title")),
                kind=str(body.get("kind")),
                payload=dict(body.get("payload", {})),
                priority=int(priority),
            )
            fname = task_filename(task)
            inbox = ensure_queue_layout(queue_root)["inbox"]
            try:
                path = _write_task_atomic(inbox, task, fname)
            except FileExistsError:
                self._send_json(409, {"ok": False, "error": "task file already exists"})
                return

            rel = path.relative_to(queue_root.parent) if queue_root.parent in path.parents else path
            self._send_json(
                200,
                {
                    "ok": True,
                    "task_id": task["task_id"],
                    "path": str(rel),
                },
            )

        def _extract_task_id(self) -> str:
            path = self.path.split("?", 1)[0]
            parts = [p for p in path.split("/") if p]
            if len(parts) < 3:
                return ""
            return unquote(parts[2])

        def _handle_status(self) -> None:
            task_id = self._extract_task_id()
            if not task_id:
                self._send_json(400, {"ok": False, "error": "missing task_id"})
                return
            state, task_path = _find_task(queue_root, task_id)
            if not state or not task_path:
                self._send_json(404, {"ok": False, "error": "task not found", "task_id": task_id})
                return
            task_payload = _read_json(task_path) or {}
            out: Dict[str, Any] = {"ok": True, "task_id": task_id, "state": state}
            out["task_path"] = str(task_path)
            if task_payload:
                out["title"] = task_payload.get("title", "")
                out["kind"] = task_payload.get("kind", "")
            state_payload = _read_json(_state_file(task_path))
            if state_payload:
                out["summary"] = {
                    "ok": bool(state_payload.get("ok", False)),
                    "status": state_payload.get("status", ""),
                    "error_summary": state_payload.get("error_summary", ""),
                    "run_dir": state_payload.get("run_dir", ""),
                }
            self._send_json(200, out)

        def _handle_result(self) -> None:
            task_id = self._extract_task_id()
            if not task_id:
                self._send_json(400, {"ok": False, "error": "missing task_id"})
                return
            state, task_path = _find_task(queue_root, task_id)
            if state not in ("done", "failed") or not task_path:
                self._send_json(404, {"ok": False, "error": "result not ready", "task_id": task_id})
                return
            payload = _read_json(_state_file(task_path))
            if not payload:
                self._send_json(404, {"ok": False, "error": "result state missing", "task_id": task_id})
                return
            self._send_json(200, payload)

        def _handle_artifact(self) -> None:
            raw = self.path.split("?", 1)[0]
            marker = "/artifacts/"
            base, rel = raw.split(marker, 1)
            task_id = unquote(base.split("/")[3]) if len(base.split("/")) > 3 else ""
            if not task_id:
                self._send_json(400, {"ok": False, "error": "missing task_id"})
                return
            state, task_path = _find_task(queue_root, task_id)
            if state not in ("running", "done", "failed") or not task_path:
                self._send_json(404, {"ok": False, "error": "task not available"})
                return
            state_payload = _read_json(_state_file(task_path))
            run_dir_raw = str(state_payload.get("run_dir", "")).strip() if state_payload else ""
            run_dir = Path(run_dir_raw).resolve() if run_dir_raw else None
            if not state_payload or not run_dir_raw or not run_dir or not run_dir.exists():
                self._send_json(404, {"ok": False, "error": "run_dir not available"})
                return
            artifact_path = _safe_artifact_path(run_dir, rel)
            if not artifact_path or not artifact_path.exists() or not artifact_path.is_file():
                self._send_json(404, {"ok": False, "error": "artifact not found"})
                return

            ctype, _ = mimetypes.guess_type(str(artifact_path))
            body = artifact_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_stream(self) -> None:
            task_id = self._extract_task_id()
            if not task_id:
                self._send_json(400, {"ok": False, "error": "missing task_id"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            last_heartbeat = 0.0
            log_handle = None
            try:
                while True:
                    state, task_path = _find_task(queue_root, task_id)
                    if not state or not task_path:
                        self.wfile.write(b"event: heartbeat\ndata: task-not-found\n\n")
                        self.wfile.flush()
                        time.sleep(0.4)
                        continue

                    state_payload = _read_json(_state_file(task_path))
                    run_dir_raw = str(state_payload.get("run_dir", "")).strip() if state_payload else ""
                    run_dir = Path(run_dir_raw).resolve() if run_dir_raw else None
                    log_path = (run_dir / "logs" / "task.log") if run_dir else None

                    if log_path and log_path.exists() and log_handle is None:
                        log_handle = open(log_path, "r", encoding="utf-8", errors="replace")
                        log_handle.seek(0, os.SEEK_SET)

                    if log_handle:
                        line = log_handle.readline()
                        while line:
                            data = line.rstrip("\n").replace("\r", "")
                            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                            self.wfile.flush()
                            line = log_handle.readline()

                    now = time.time()
                    if now - last_heartbeat > 1.0:
                        tag = state if state else "waiting"
                        self.wfile.write(f"event: heartbeat\ndata: {tag}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        last_heartbeat = now
                    if state in ("done", "failed"):
                        self.wfile.write(f"event: complete\ndata: {state}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        return
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                return
            finally:
                try:
                    if log_handle:
                        log_handle.close()
                except Exception:
                    pass

    return BridgeHandler


def run_server(host: str = "127.0.0.1", port: int = 8844, queue_root: str = "queue") -> int:
    qroot = Path(queue_root).resolve()
    handler = _make_handler(qroot)
    server = ThreadingHTTPServer((host, int(port)), handler)
    token_on = "on" if _auth_enabled() else "off"
    print(f"AEL Bridge listening on http://{host}:{int(port)} (token auth: {token_on})")
    print(f"Bridge queue root: {qroot}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ael.bridge_server")
    parser.add_argument("--host", default=os.environ.get("AEL_BRIDGE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AEL_BRIDGE_PORT", "8844")))
    parser.add_argument("--queue", default=os.environ.get("AEL_QUEUE_ROOT", "queue"))
    args = parser.parse_args()
    return run_server(host=args.host, port=args.port, queue_root=args.queue)


if __name__ == "__main__":
    raise SystemExit(main())
