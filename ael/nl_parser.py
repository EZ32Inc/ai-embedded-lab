from __future__ import annotations

import re
from typing import Dict


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def parse_user_prompt(prompt: str) -> Dict:
    text = _normalize(prompt)
    if not text:
        return {"title": "empty prompt", "kind": "codex", "payload": {"prompt": prompt}}

    board = ""
    for candidate in ("stm32f103", "stm32", "esp32s3", "esp32", "rp2040", "pico"):
        if candidate in text:
            board = candidate
            break

    test = ""
    if "gpio" in text:
        test = "gpio"
    elif "uart" in text:
        test = "uart"

    if "run" in text and test:
        title_parts = [test, "test"]
        if board:
            title_parts.append(board)
        return {
            "title": " ".join(title_parts),
            "kind": "runplan",
            "payload": {
                "test": test,
                "board": board,
                "prompt": prompt,
            },
        }

    return {
        "title": prompt[:80] if prompt else "codex task",
        "kind": "codex",
        "payload": {"prompt": prompt, "repo_root": "."},
    }
