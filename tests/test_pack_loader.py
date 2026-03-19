from __future__ import annotations

import json
from pathlib import Path

import pytest

from ael.pack_loader import load_pack


def test_load_pack_supports_single_parent_extends(tmp_path: Path):
    base = tmp_path / "base.json"
    child = tmp_path / "child.json"
    base.write_text(
        json.dumps(
            {
                "name": "base_pack",
                "preflight": {"enabled": False},
                "tests": ["tests/plans/stm32f103rct6_mailbox.json"],
                "notes": "base",
            }
        ),
        encoding="utf-8",
    )
    child.write_text(
        json.dumps(
            {
                "extends": "base.json",
                "name": "child_pack",
                "board": "stm32f103rct6_stlink",
                "notes": "child",
            }
        ),
        encoding="utf-8",
    )

    payload = load_pack(child)
    assert payload["name"] == "child_pack"
    assert payload["board"] == "stm32f103rct6_stlink"
    assert payload["tests"] == ["tests/plans/stm32f103rct6_mailbox.json"]
    assert payload["preflight"]["enabled"] is False
    assert payload["notes"] == "child"


def test_load_pack_detects_extends_cycle(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"extends": "b.json", "name": "a"}), encoding="utf-8")
    b.write_text(json.dumps({"extends": "a.json", "name": "b"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_pack(a)
