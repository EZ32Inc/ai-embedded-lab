from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from ael import paths as ael_paths


SCHEMA_VERSION = "ael.workflow_archive.event.v0.2"
_APPEND_LOCK = threading.Lock()


def archive_root() -> Path:
    env = str(os.getenv("AEL_WORKFLOW_ARCHIVE_ROOT", "")).strip()
    root = Path(env).expanduser() if env else (ael_paths.repo_root() / "workflow_archive")
    root.mkdir(parents=True, exist_ok=True)
    return root


def global_events_path() -> Path:
    return archive_root() / "events.jsonl"


def run_events_path(run_root: str | Path) -> Path:
    return Path(run_root) / "workflow_events.jsonl"


def _is_json_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _normalize(value: Any) -> Any:
    if _is_json_scalar(value):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            norm = _normalize(item)
            if norm is not None:
                out[str(key)] = norm
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            norm = _normalize(item)
            if norm is not None:
                out.append(norm)
        return out
    return str(value)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def append_event(event: dict, run_root: str | Path | None = None) -> dict:
    record = {"schema": SCHEMA_VERSION, **_normalize(event)}
    if "timestamp" not in record:
        record["timestamp"] = datetime.now().isoformat()
    with _APPEND_LOCK:
        _append_jsonl(global_events_path(), record)
        if run_root:
            _append_jsonl(run_events_path(run_root), record)
    return record


def env_conversation_context() -> dict:
    context = {
        "session_id": str(os.getenv("AEL_SESSION_ID", "")).strip() or None,
        "task_id": str(os.getenv("AEL_TASK_ID", "")).strip() or None,
        "user_request": str(os.getenv("AEL_USER_REQUEST", "")).strip() or None,
        "ai_response": str(os.getenv("AEL_AI_RESPONSE", "")).strip() or None,
        "user_confirmation": str(os.getenv("AEL_USER_CONFIRMATION", "")).strip() or None,
        "user_correction": str(os.getenv("AEL_USER_CORRECTION", "")).strip() or None,
        "ai_next_action": str(os.getenv("AEL_AI_NEXT_ACTION", "")).strip() or None,
    }
    return {k: v for k, v in context.items() if v is not None}


def workflow_event(
    *,
    actor: str,
    action: str,
    text: str | None = None,
    status: str | None = None,
    stage: str | None = None,
    extra: dict | None = None,
) -> dict:
    event = {
        "category": "workflow",
        "actor": actor,
        "action": action,
    }
    if status is not None:
        event["status"] = status
    if stage is not None:
        event["stage"] = stage
    if text is not None:
        event["message"] = {"text": text}
    if isinstance(extra, dict):
        event.update(extra)
    return event


def runtime_event(
    *,
    action: str,
    status: str | None = None,
    stage: str | None = None,
    extra: dict | None = None,
) -> dict:
    event = {
        "category": "runtime",
        "actor": "ael",
        "action": action,
    }
    if status is not None:
        event["status"] = status
    if stage is not None:
        event["stage"] = stage
    if isinstance(extra, dict):
        event.update(extra)
    return event


def read_events(limit: int = 20, run_id: str | None = None, source: str = "global") -> list[dict]:
    if source == "global":
        path = global_events_path()
    else:
        path = Path(source)
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            if run_id and str(record.get("run_id") or "") != run_id:
                continue
            records.append(record)
    if limit > 0:
        records = records[-limit:]
    return records
