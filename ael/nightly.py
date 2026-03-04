from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ael.agent import execute_task_payload
from ael.git_ops import (
    checkout,
    commit_all,
    create_branch,
    current_branch,
    diffstat_head,
    repo_root,
    require_clean_or_stash,
    restore_stash,
    safe_branch_name,
)
from ael.nightly_report import write_nightly_report


@dataclass
class NightlyConfig:
    date_str: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    max_plans: int = 3
    allow_on_master: bool = False
    stash_dirty: bool = True
    work_branch_prefix: str = "agent"
    backlog_sources: List[str] = field(default_factory=lambda: ["queue/inbox"])
    dry_run: bool = False
    verbose: bool = False
    queue_path: str = "queue"
    report_root: str = "reports"


def _read_json(path: Path) -> Dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _collect_backlog(cfg: NightlyConfig) -> List[Dict]:
    root = repo_root()
    items: List[Dict] = []
    for src in cfg.backlog_sources:
        p = Path(src)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            continue
        if p.is_dir():
            files = [x for x in p.glob("*.json") if not x.name.endswith(".state.json")]
            files += list(p.glob("*/task.json"))
        else:
            files = [p]
        for f in sorted(files):
            data = _read_json(f)
            if data:
                items.append(data)
    selected: List[Dict] = []
    for it in items:
        if str(it.get("kind", "")).strip() == "plan":
            selected.append(dict(it))
        else:
            prompt = str(it.get("title", "")).strip()
            payload = it.get("payload", {}) if isinstance(it.get("payload"), dict) else {}
            prompt = prompt or str(payload.get("prompt", "")).strip() or json.dumps(it, sort_keys=True)
            selected.append({"title": prompt[:80], "kind": "plan", "payload": {"prompt": prompt}})
    if not selected:
        selected.append(
            {
                "title": "Maintenance nightly plan",
                "kind": "plan",
                "payload": {"prompt": "Maintenance: run gates, scan TODOs, propose next improvements"},
            }
        )
    return selected[: max(1, int(cfg.max_plans))]


def _unique_branch(base_name: str) -> str:
    branch = base_name
    for i in range(1, 50):
        probe = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
        )
        if int(probe.returncode) != 0:
            return branch
        branch = f"{base_name}-{i+1}"
    return branch


def run_nightly(cfg: NightlyConfig) -> Dict:
    summary: Dict = {
        "ok": True,
        "started_at": datetime.now().isoformat(),
        "finished_at": "",
        "plans": [],
        "report_path": "",
    }

    base = current_branch()
    if base in ("master", "main") and not (cfg.allow_on_master or cfg.dry_run):
        summary["ok"] = False
        summary["finished_at"] = datetime.now().isoformat()
        summary["error_summary"] = "nightly refused on master/main; use --allow-on-master or --dry-run"
        return summary

    plans = _collect_backlog(cfg)
    stash_info = {"stashed": False, "stash_ref": None}
    if not cfg.dry_run:
        stash_info = require_clean_or_stash(cfg.stash_dirty)

    try:
        for idx, plan_task in enumerate(plans, start=1):
            title = str(plan_task.get("title", "")).strip() or f"plan_{idx}"
            task_id = str(plan_task.get("task_id", "")).strip() or datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{idx:02d}"
            branch = _unique_branch(safe_branch_name(cfg.work_branch_prefix, f"{task_id}-{title}", cfg.date_str.replace("-", "")))
            entry = {
                "title": title,
                "task_id": task_id,
                "branch": branch,
                "status": "PLANNED",
                "commit": "",
                "run_dir": "",
                "report_path": "",
                "error_summary": "",
                "diffstat": "",
            }
            if cfg.dry_run:
                entry["status"] = "OK"
                summary["plans"].append(entry)
                continue

            try:
                create_branch(branch)
            except Exception as exc:
                entry["status"] = "FAILED"
                entry["error_summary"] = f"branch creation failed: {exc}"
                summary["plans"].append(entry)
                summary["ok"] = False
                checkout(base)
                continue

            run = execute_task_payload(
                {"task_id": task_id, "title": title, "kind": "plan", "payload": dict(plan_task.get("payload", {}))},
                queue_path=cfg.queue_path,
                report_root=cfg.report_root,
                task_index=idx,
                verbose=cfg.verbose,
            )
            state = run.get("state", {}) if isinstance(run.get("state"), dict) else {}
            ok = bool(state.get("ok", False))
            entry["status"] = "OK" if ok else "FAILED"
            entry["run_dir"] = str(state.get("run_dir", ""))
            entry["error_summary"] = str(state.get("error_summary", ""))
            entry["report_path"] = str((state.get("key_artifacts", {}) or {}).get("plan_report", ""))

            commit = commit_all(f"chore(nightly): {title}")
            entry["commit"] = commit or ""
            if commit:
                entry["diffstat"] = diffstat_head()
            if not ok:
                summary["ok"] = False
            summary["plans"].append(entry)
            checkout(base)
    finally:
        if not cfg.dry_run:
            checkout(base)
            restore_stash(stash_info)

    summary["finished_at"] = datetime.now().isoformat()
    report_path = Path(cfg.report_root) / f"nightly_{cfg.date_str}.md"
    write_nightly_report(cfg.date_str, summary, report_path)
    summary["report_path"] = str(report_path)
    return summary
