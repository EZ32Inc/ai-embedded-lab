from __future__ import annotations

import re
from typing import Dict, List


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _detect_board(text: str) -> str:
    for candidate in ("stm32f103", "stm32", "esp32s3", "esp32", "rp2040", "pico"):
        if candidate in text:
            return candidate
    return ""


def _detect_test(text: str) -> str:
    if "gpio" in text:
        return "gpio"
    if "uart" in text:
        return "uart"
    return "general"


def _noop_runplan(prompt: str, test: str, board: str) -> Dict:
    note = f"{test} test {board}".strip()
    if not note:
        note = prompt.strip() or "plan run"
    return {
        "version": "runplan/0.1",
        "plan_id": "plan_generated",
        "created_at": "",
        "inputs": {"prompt": prompt, "test": test, "board": board},
        "selected": {"test_config": "plan/noop"},
        "context": {},
        "steps": [{"name": "check_plan_generated", "type": "check.noop", "inputs": {"note": note}}],
        "recovery_policy": {"enabled": False},
        "meta": {},
    }


def generate_plan(prompt: str) -> List[Dict]:
    text = _norm(prompt)
    board = _detect_board(text)
    test = _detect_test(text)

    return [
        {
            "kind": "codex",
            "title": f"generate {test} task assets",
            "payload": {
                "prompt": f"Prepare changes for {test} testing on {board or 'target board'}. Original goal: {prompt}",
                "repo_root": ".",
            },
        },
        {
            "kind": "runplan",
            "title": f"run {test} test",
            "payload": {
                "test": test,
                "board": board,
                "runplan": _noop_runplan(prompt, test=test, board=board),
            },
        },
        {
            "kind": "noop",
            "title": "verify results",
            "payload": {"note": f"verify plan outcome for: {prompt}"},
        },
    ]
