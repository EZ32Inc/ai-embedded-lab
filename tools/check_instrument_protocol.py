#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP_KEYS = ("id", "name", "version", "transports", "capabilities")
REQUIRED_CAP_KEYS = ("name", "inputs_schema", "outputs_schema")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _validate_capability(cap: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in REQUIRED_CAP_KEYS:
        if key not in cap:
            errors.append(f"missing capability key: {key}")
    name = cap.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("capability name must be non-empty string")
    for schema_key in ("inputs_schema", "outputs_schema"):
        schema_val = cap.get(schema_key)
        if not isinstance(schema_val, dict):
            errors.append(f"{schema_key} must be object")
        elif schema_val.get("type") != "object":
            errors.append(f"{schema_key}.type must be 'object'")
    return errors


def _validate_manifest(path: Path, data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    for key in ("id", "name", "version"):
        val = data.get(key)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{key} must be non-empty string")

    transports = data.get("transports")
    if not isinstance(transports, list) or not transports:
        errors.append("transports must be non-empty list")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be non-empty list")
    else:
        for idx, cap in enumerate(capabilities):
            if not isinstance(cap, dict):
                errors.append(f"capabilities[{idx}] must be object")
                continue
            for err in _validate_capability(cap):
                errors.append(f"capabilities[{idx}]: {err}")

    return errors


def main() -> int:
    manifest_path = _repo_root() / "ael" / "instruments" / "sim_manifest.json"
    data = _load_json(manifest_path)
    if data is None:
        print("[INSTRUMENT_PROTOCOL] FAIL")
        print(f"invalid JSON manifest: {manifest_path}")
        return 1

    errors = _validate_manifest(manifest_path, data)
    if errors:
        print("[INSTRUMENT_PROTOCOL] FAIL")
        print(json.dumps({str(manifest_path): errors}, indent=2, sort_keys=True))
        return 1

    print("[INSTRUMENT_PROTOCOL] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
