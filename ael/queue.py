from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


QUEUE_DIRS = ("inbox", "running", "done", "failed")


def ensure_queue_layout(queue_root: str | Path) -> Dict[str, Path]:
    root = Path(queue_root)
    root.mkdir(parents=True, exist_ok=True)
    out: Dict[str, Path] = {}
    for name in QUEUE_DIRS:
        p = root / name
        p.mkdir(parents=True, exist_ok=True)
        out[name] = p
    return out


def _state_path(task_path: Path) -> Path:
    if task_path.suffix == ".json":
        return task_path.with_suffix(".state.json")
    return task_path.parent / f"{task_path.name}.state.json"


def write_state(task_path: str | Path, payload: Dict) -> Path:
    p = _state_path(Path(task_path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return p


def _task_priority(path: Path) -> Tuple[int, str]:
    default = (100, path.name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    if not isinstance(data, dict):
        return default
    try:
        p = int(data.get("priority", 100))
    except Exception:
        p = 100
    return (p, path.name)


def list_inbox_tasks(queue_root: str | Path) -> List[Path]:
    paths = ensure_queue_layout(queue_root)
    files = [p for p in paths["inbox"].glob("*.json") if p.is_file()]
    files.sort(key=_task_priority)
    return files


def claim_task(task_inbox_path: str | Path, queue_root: str | Path) -> Path:
    p = Path(task_inbox_path)
    paths = ensure_queue_layout(queue_root)
    dst = paths["running"] / p.name
    p.rename(dst)
    return dst


def finalize_task(task_running_path: str | Path, queue_root: str | Path, ok: bool) -> Path:
    p = Path(task_running_path)
    paths = ensure_queue_layout(queue_root)
    dst_dir = paths["done"] if ok else paths["failed"]
    dst = dst_dir / p.name
    p.rename(dst)
    return dst


def load_task(task_path: str | Path) -> Optional[Dict]:
    p = Path(task_path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def move_state(task_src_path: str | Path, task_dst_path: str | Path, payload: Dict) -> Path:
    src_state = _state_path(Path(task_src_path))
    dst_state = _state_path(Path(task_dst_path))
    dst_state.parent.mkdir(parents=True, exist_ok=True)
    dst_state.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if src_state.exists() and src_state != dst_state:
        try:
            src_state.unlink()
        except Exception:
            pass
    return dst_state
