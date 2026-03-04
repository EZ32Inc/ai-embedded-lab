from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _manifest_path(instrument_id: str) -> Path:
    if not instrument_id or not str(instrument_id).strip():
        raise ValueError("instrument_id is required")
    return _repo_root() / "configs" / "instruments" / f"{instrument_id}.json"


def load_manifest(instrument_id: str) -> Dict[str, Any]:
    path = _manifest_path(instrument_id)
    if not path.exists():
        raise FileNotFoundError(f"instrument manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"instrument manifest must be a JSON object: {path}")
    return data
