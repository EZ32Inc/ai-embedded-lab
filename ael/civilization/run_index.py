"""Civilization Engine — Run Aggregation Index.

Stores per-experiment statistics so repeated runs strengthen existing
Experience Engine records instead of appending duplicate entries.

Index file: ael/civilization/data/run_index.json

Schema per entry:
{
  "rp2040_pico|rp2040_gpio_signature": {
    "exp_id":        "feb3d816-...",   # canonical EE record id (success)
    "success_count": 8,
    "failure_count": 0,
    "last_seen":     1774200000.0,     # unix timestamp
    "confidence":    0.9,              # locally tracked, mirrors EE confidence
    "known_failures": {
      "preflight_failed": {
        "exp_id":   "abc123-...",      # EE record id for this failure kind
        "count":    2,
        "last_raw": "..."              # most recent raw description
      }
    }
  }
}
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

_INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "run_index.json")


def _load() -> dict:
    try:
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(_INDEX_PATH), exist_ok=True)
    with open(_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def make_signature(board_id: str, test_name: str) -> str:
    return f"{board_id}|{test_name}"


def get(signature: str) -> Optional[dict]:
    """Return the index entry for a signature, or None if not found."""
    return _load().get(signature)


def get_run_stats(board_id: str, test_name: str) -> dict:
    """Return run statistics for display in CivilizationContext.summary_lines()."""
    sig = make_signature(board_id, test_name)
    entry = get(sig)
    if not entry:
        return {}
    return {
        "success_count": entry.get("success_count", 0),
        "failure_count": entry.get("failure_count", 0),
        "last_seen":     entry.get("last_seen"),
        "confidence":    entry.get("confidence", 0.5),
    }


def record_success(board_id: str, test_name: str, exp_id: str) -> bool:
    """Register a successful run.

    Returns True if this was an aggregate update (existing record found),
    False if a new index entry was created.
    """
    sig = make_signature(board_id, test_name)
    data = _load()
    entry = data.get(sig)

    if entry and entry.get("exp_id"):
        # Aggregate: strengthen the existing record
        entry["success_count"] = entry.get("success_count", 0) + 1
        entry["last_seen"] = time.time()
        entry["confidence"] = min(1.0, round(entry.get("confidence", 0.5) + 0.1, 2))
        data[sig] = entry
        _save(data)
        return True  # was aggregate
    else:
        # First success: initialise entry
        data[sig] = {
            "exp_id":         exp_id,
            "success_count":  1,
            "failure_count":  entry.get("failure_count", 0) if entry else 0,
            "last_seen":      time.time(),
            "confidence":     0.5,
            "known_failures": entry.get("known_failures", {}) if entry else {},
        }
        _save(data)
        return False  # was new


def record_failure(
    board_id: str,
    test_name: str,
    failure_kind: str,
    exp_id: str,
    last_raw: str,
) -> bool:
    """Register a failed run.

    Returns True if this failure_kind was already known (aggregate update),
    False if it's a new failure_kind (new EE record warranted).
    """
    sig = make_signature(board_id, test_name)
    data = _load()
    entry = data.get(sig) or {
        "exp_id":         None,
        "success_count":  0,
        "failure_count":  0,
        "last_seen":      time.time(),
        "confidence":     0.5,
        "known_failures": {},
    }

    entry["failure_count"] = entry.get("failure_count", 0) + 1
    entry["last_seen"] = time.time()

    known = entry.setdefault("known_failures", {})
    fk = failure_kind or "unknown"

    if fk in known:
        # Aggregate: same failure kind seen before
        known[fk]["count"] = known[fk].get("count", 1) + 1
        known[fk]["last_raw"] = last_raw
        data[sig] = entry
        _save(data)
        return True  # was aggregate
    else:
        # New failure kind
        known[fk] = {"exp_id": exp_id, "count": 1, "last_raw": last_raw}
        data[sig] = entry
        _save(data)
        return False  # was new


def get_failure_exp_id(board_id: str, test_name: str, failure_kind: str) -> Optional[str]:
    """Return the EE record id for a known failure kind, or None."""
    sig = make_signature(board_id, test_name)
    entry = get(sig)
    if not entry:
        return None
    fk = failure_kind or "unknown"
    known = entry.get("known_failures", {})
    rec = known.get(fk)
    return rec.get("exp_id") if rec else None


def get_success_exp_id(board_id: str, test_name: str) -> Optional[str]:
    """Return the canonical success EE record id, or None."""
    entry = get(make_signature(board_id, test_name))
    return entry.get("exp_id") if entry else None
