from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=str(repo_root()), capture_output=True, text=True)
    if check and int(proc.returncode) != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git failed").strip())
    return proc


def current_branch() -> str:
    return (_run_git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout or "").strip()


def is_dirty() -> bool:
    return bool((_run_git(["status", "--porcelain"]).stdout or "").strip())


def require_clean_or_stash(stash: bool) -> Dict:
    if not is_dirty():
        return {"stashed": False, "stash_ref": None}
    if not stash:
        raise RuntimeError("working tree is dirty")
    marker = "ael-nightly-" + datetime.now().strftime("%Y%m%d_%H%M%S")
    _run_git(["stash", "push", "-u", "-m", marker])
    stash_ref = None
    for line in (_run_git(["stash", "list"], check=False).stdout or "").splitlines():
        if marker in line:
            stash_ref = line.split(":", 1)[0].strip()
            break
    return {"stashed": True, "stash_ref": stash_ref}


def restore_stash(info: Dict) -> None:
    if not isinstance(info, dict) or not bool(info.get("stashed", False)):
        return
    _run_git(["stash", "pop", str(info.get("stash_ref") or "stash@{0}")], check=False)


def create_branch(branch: str) -> None:
    _run_git(["checkout", "-b", branch])


def checkout(branch: str) -> None:
    _run_git(["checkout", branch])


def _commit_candidates() -> List[str]:
    out = _run_git(["status", "--porcelain"], check=False).stdout or ""
    paths: List[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if not path:
            continue
        if path.startswith("queue/") or path.startswith("runs/") or path.startswith("pack_runs/"):
            continue
        if path.startswith("reports/nightly_") and path.endswith(".json"):
            continue
        if path.startswith(("ael/", "tools/", "docs/")):
            paths.append(path)
    return sorted(set(paths))


def commit_all(message: str, allow_empty: bool = False) -> Optional[str]:
    paths = _commit_candidates()
    if paths:
        _run_git(["add", "--", *paths], check=False)
    staged = (_run_git(["diff", "--cached", "--name-only"], check=False).stdout or "").strip()
    if not staged and not allow_empty:
        return None
    cmd = ["commit", "-m", message] + (["--allow-empty"] if allow_empty else [])
    proc = _run_git(cmd, check=False)
    if int(proc.returncode) != 0:
        return None
    return (_run_git(["rev-parse", "HEAD"]).stdout or "").strip() or None


def diffstat_head() -> str:
    return (_run_git(["show", "--stat", "--oneline", "--no-color", "-1"], check=False).stdout or "").strip()


def safe_branch_name(prefix: str, slug: str, date: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in slug.lower()).strip("-")
    cleaned = "-".join([p for p in cleaned.split("-") if p]) or "task"
    return f"{prefix}/{date}/{cleaned[:48]}"
