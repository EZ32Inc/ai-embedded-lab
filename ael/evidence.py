from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_evidence(run_dir: str | Path, filename: str, payload: Dict[str, Any] | Any) -> str:
    if not filename or not str(filename).strip():
        raise ValueError("filename is required")

    base = Path(run_dir)
    artifacts_dir = base / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    out_path = artifacts_dir / str(filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    return str(out_path)
