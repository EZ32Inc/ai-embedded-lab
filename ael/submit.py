from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from urllib import request
from urllib.error import HTTPError, URLError

from ael.nl_parser import parse_user_prompt


def _post_json(url: str, payload: Dict) -> Tuple[int, Dict]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = (resp.read() or b"{}").decode("utf-8")
            out = json.loads(body) if body else {}
            return int(resp.status), out if isinstance(out, dict) else {}
    except HTTPError as exc:
        try:
            err = json.loads((exc.read() or b"{}").decode("utf-8"))
        except Exception:
            err = {"ok": False, "error": str(exc)}
        return int(exc.code), err if isinstance(err, dict) else {"ok": False, "error": str(exc)}
    except URLError as exc:
        return 0, {"ok": False, "error": f"connection failed: {exc}"}


def _noop_runplan_from_prompt(prompt: str, board: str, test: str) -> Dict:
    note = prompt.strip() or "nl submit"
    return {
        "version": "runplan/0.1",
        "plan_id": f"nl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {"prompt": prompt, "board": board, "test": test},
        "selected": {"test_config": "nl/noop"},
        "context": {},
        "steps": [
            {
                "name": "check_nl_noop",
                "type": "check.noop",
                "inputs": {"note": note},
            }
        ],
        "recovery_policy": {"enabled": False},
        "meta": {},
    }


def build_bridge_task_from_input(user_input: str, json_mode: bool = False) -> Dict:
    text = (user_input or "").strip()
    if json_mode:
        p = Path(text)
        if p.exists():
            payload = json.loads(p.read_text(encoding="utf-8"))
        else:
            payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("JSON submit input must be an object")
        return payload

    parsed = parse_user_prompt(text)
    kind = str(parsed.get("kind", "")).strip()
    title = str(parsed.get("title", "")).strip() or "task"
    payload = parsed.get("payload", {}) if isinstance(parsed.get("payload"), dict) else {}
    if kind == "runplan":
        runplan = payload.get("runplan")
        if not isinstance(runplan, dict):
            runplan = _noop_runplan_from_prompt(text, str(payload.get("board", "")), str(payload.get("test", "")))
        return {"title": title, "kind": "runplan", "payload": {"runplan": runplan}, "priority": 0}
    if kind == "codex":
        codex_payload = {
            "repo_root": str(payload.get("repo_root", ".")),
            "prompt": str(payload.get("prompt", text)),
        }
        return {"title": title, "kind": "codex", "payload": codex_payload, "priority": 0}
    return {"title": title, "kind": "noop", "payload": {}, "priority": 0}


def submit_to_bridge(user_input: str, api_url: str, json_mode: bool = False) -> Tuple[int, Dict]:
    task = build_bridge_task_from_input(user_input=user_input, json_mode=json_mode)
    return _post_json(api_url, task)
