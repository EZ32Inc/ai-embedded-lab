from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merge_pack_dicts(base: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in child.items():
        if key == "extends":
            continue
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _merge_pack_dicts(base_value, value)
        else:
            merged[key] = value
    return merged


def load_pack(path: str | Path) -> dict[str, Any]:
    pack_path = Path(path).resolve()
    return _load_pack_recursive(pack_path, stack=[])


def _load_pack_recursive(path: Path, stack: list[Path]) -> dict[str, Any]:
    if path in stack:
        cycle = " -> ".join(str(item) for item in [*stack, path])
        raise ValueError(f"pack extends cycle detected: {cycle}")

    payload = _load_json(path)
    if not payload:
        return {}

    extends = payload.get("extends")
    if not extends:
        return payload
    if not isinstance(extends, str):
        raise ValueError(f"pack extends must be a string: {path}")

    parent_path = (path.parent / extends).resolve()
    parent_payload = _load_pack_recursive(parent_path, stack=[*stack, path])
    merged = _merge_pack_dicts(parent_payload, payload)
    merged["_resolved_from"] = str(path)
    merged["_resolved_extends"] = str(parent_path)
    return merged
