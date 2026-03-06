from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runs_root() -> Path:
    env = str(os.getenv("AEL_RUNS_ROOT", "")).strip()
    if env:
        return Path(env).expanduser()
    # Deterministic default: always keep runs inside this repo.
    root = repo_root() / "runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def artifacts_root() -> Path:
    return repo_root() / "artifacts"


def queue_root() -> Path:
    return repo_root() / "queue"


def reports_root() -> Path:
    return repo_root() / "reports"
