from __future__ import annotations

import re
import secrets
from datetime import datetime
from typing import Any, Dict, Tuple


BRIDGE_VERSION = "bridge/0.1"
BRIDGE_KINDS = {"runplan", "codex", "noop"}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def generate_task_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{secrets.token_hex(3)}"


def slugify(value: str) -> str:
    raw = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", raw)
    text = text.strip("-")
    return text or "task"


def is_bridge_task(task: Dict[str, Any]) -> bool:
    if not isinstance(task, dict):
        return False
    if not isinstance(task.get("title"), str):
        return False
    if task.get("kind") not in BRIDGE_KINDS:
        return False
    return isinstance(task.get("payload"), dict)


def validate_submit_request(body: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(body, dict):
        return False, "request body must be a JSON object"
    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        return False, "title is required"
    kind = body.get("kind")
    if kind not in BRIDGE_KINDS:
        return False, "kind must be one of: runplan, codex, noop"
    payload = body.get("payload")
    if not isinstance(payload, dict):
        return False, "payload must be a JSON object"
    return True, ""


def build_task(*, title: str, kind: str, payload: Dict[str, Any], priority: int = 0, task_id: str | None = None) -> Dict[str, Any]:
    if kind not in BRIDGE_KINDS:
        raise ValueError("invalid bridge task kind")
    task = {
        "task_id": str(task_id or generate_task_id()),
        "title": str(title).strip(),
        "kind": kind,
        "created_at": now_iso(),
        "payload": dict(payload),
        "priority": int(priority),
        "meta": {
            "priority": int(priority),
            "source": "bridge",
            "bridge_version": BRIDGE_VERSION,
        },
    }
    return task


def task_filename(task: Dict[str, Any]) -> str:
    task_id = str(task.get("task_id", "task")).strip() or "task"
    slug = slugify(str(task.get("title", "task")))
    return f"{task_id}__{slug}.json"


def noop_plan(task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(task.get("task_id", "bridge-noop"))
    title = str(task.get("title", "bridge noop"))
    return {
        "version": "runplan/0.1",
        "plan_id": task_id,
        "created_at": now_iso(),
        "inputs": {"task_id": task_id},
        "selected": {"test_config": "bridge/noop"},
        "context": {},
        "steps": [
            {
                "name": "check_bridge_noop",
                "type": "check.noop",
                "inputs": {"note": title},
            }
        ],
        "recovery_policy": {"enabled": False},
        "meta": {},
    }
