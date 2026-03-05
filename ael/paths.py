from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runs_root() -> Path:
    return repo_root() / "runs"


def artifacts_root() -> Path:
    return repo_root() / "artifacts"


def queue_root() -> Path:
    return repo_root() / "queue"


def reports_root() -> Path:
    return repo_root() / "reports"
