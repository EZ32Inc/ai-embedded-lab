from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_PROTOCOL = "aip/0.1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _manifest_files() -> List[Path]:
    base = _repo_root() / "configs" / "instruments"
    if not base.exists():
        return []
    return sorted(base.glob("*.json"))


def _load_json(path: Path) -> Dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _has_evidence_path(data: Dict[str, Any]) -> bool:
    if isinstance(data.get("evidence_path"), str) and data.get("evidence_path").strip():
        return True
    evidence = data.get("evidence")
    if isinstance(evidence, dict):
        path = evidence.get("path")
        if isinstance(path, str) and path.strip():
            return True
    return False


def _validate_one(path: Path, data: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    protocol = data.get("protocol")
    if protocol != REQUIRED_PROTOCOL:
        errs.append(f"protocol must be '{REQUIRED_PROTOCOL}', got '{protocol}'")

    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        errs.append("capabilities must be a non-empty list")

    if not _has_evidence_path(data):
        errs.append("evidence path must be defined (evidence_path or evidence.path)")

    return errs


def main() -> int:
    files = _manifest_files()
    failures: Dict[str, List[str]] = {}

    for p in files:
        data = _load_json(p)
        if data is None:
            failures[str(p)] = ["invalid JSON object"]
            continue
        errs = _validate_one(p, data)
        if errs:
            failures[str(p)] = errs

    if failures:
        print("[INSTRUMENT_CONTRACT] FAIL")
        print(json.dumps(failures, indent=2, sort_keys=True))
        return 1

    print("[INSTRUMENT_CONTRACT] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
