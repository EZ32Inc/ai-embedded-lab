from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ael.adapter_registry import AdapterRegistry
from ael.queue import (
    claim_task,
    ensure_queue_layout,
    finalize_task,
    list_inbox_tasks,
    load_task,
    move_state,
    write_state,
)
from ael.reporting import append_task_result
from ael.runner import run_plan


def _now_iso() -> str:
    return datetime.now().isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_run_dir(path_value: str) -> bool:
    p = Path(path_value)
    if not p.is_absolute():
        return False
    try:
        resolved = p.resolve()
    except Exception:
        return False
    repo = _repo_root().resolve()
    tmp = Path("/tmp").resolve()
    return str(resolved).startswith(str(repo)) or str(resolved).startswith(str(tmp))


def _default_run_dir(task_id: str) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in task_id)
    return _repo_root() / "runs" / f"{ts}_agent_{safe_id}"


def _load_plan(task: Dict, task_dir: Path) -> Tuple[Optional[Dict], str]:
    if isinstance(task.get("plan"), dict):
        return dict(task.get("plan")), ""

    plan_path = task.get("plan_path")
    if not plan_path:
        return None, "plan or plan_path is required"

    p = Path(str(plan_path))
    if not p.is_absolute():
        p = (task_dir / p).resolve()
    if not p.exists():
        return None, f"plan_path not found: {p}"
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"failed to load plan_path: {exc}"
    if not isinstance(payload, dict):
        return None, "plan_path does not contain a JSON object"
    return payload, ""


def _run_commands(commands: List[str], log_path: Path) -> Tuple[bool, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        for cmd in commands:
            f.write(f"$ {cmd}\n")
            f.flush()
            try:
                p = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(_repo_root()),
                    capture_output=True,
                    text=True,
                )
            except Exception as exc:
                f.write(f"command execution failed: {exc}\n")
                return False, f"command execution failed: {exc}"

            if p.stdout:
                f.write(p.stdout)
            if p.stderr:
                f.write(p.stderr)
            f.write(f"[exit_code] {p.returncode}\n\n")
            f.flush()
            if int(p.returncode) != 0:
                return False, f"validation command failed: {cmd}"

    return True, ""


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _task_validate(task: Dict) -> Tuple[List[str], List[str]]:
    validate = task.get("validate", {}) if isinstance(task.get("validate"), dict) else {}
    pre = validate.get("pre", []) if isinstance(validate.get("pre"), list) else []
    post = validate.get("post", []) if isinstance(validate.get("post"), list) else []
    pre_cmds = [str(x) for x in pre if isinstance(x, (str, int, float))]
    post_cmds = [str(x) for x in post if isinstance(x, (str, int, float))]
    return pre_cmds, post_cmds


def _process_task_file(task_inbox_path: Path, queue_root: Path, report_root: Path, verbose: bool = False) -> bool:
    running_task = claim_task(task_inbox_path, queue_root)
    started = time.monotonic()
    started_at = _now_iso()

    running_state = {
        "task_id": "",
        "started_at": started_at,
        "finished_at": "",
        "ok": False,
        "run_dir": "",
        "status": "running",
        "error_summary": "",
        "key_artifacts": {},
    }
    write_state(running_task, running_state)

    task = load_task(running_task)
    task_id = running_task.stem
    if isinstance(task, dict) and task.get("task_id"):
        task_id = str(task.get("task_id"))
    running_state["task_id"] = task_id

    def finalize(ok: bool, run_dir: Optional[Path], error_summary: str, artifacts: Dict[str, str]) -> bool:
        finished_at = _now_iso()
        duration_s = round(time.monotonic() - started, 3)
        running_state.update(
            {
                "finished_at": finished_at,
                "ok": bool(ok),
                "run_dir": str(run_dir) if run_dir else "",
                "error_summary": error_summary,
                "key_artifacts": artifacts,
                "duration_s": duration_s,
                "status": "done" if ok else "failed",
            }
        )

        final_task = finalize_task(running_task, queue_root, ok=ok)
        move_state(running_task, final_task, running_state)
        append_task_result(report_root, running_state)
        if verbose:
            print(f"Agent: task {task_id} -> {'DONE' if ok else 'FAILED'}")
        return ok

    if not isinstance(task, dict):
        return finalize(False, None, "invalid task JSON", {})

    if task.get("task_version") != "agenttask/0.1":
        return finalize(False, None, "unsupported task_version", {})

    plan, plan_err = _load_plan(task, running_task.parent)
    if not plan:
        return finalize(False, None, plan_err or "plan resolution failed", {})

    run_dir_hint = None
    meta = plan.get("meta", {}) if isinstance(plan.get("meta"), dict) else {}
    if isinstance(meta.get("run_dir"), str):
        run_dir_hint = meta.get("run_dir")
    if isinstance(task.get("run_dir_hint"), str) and task.get("run_dir_hint"):
        run_dir_hint = str(task.get("run_dir_hint"))

    if run_dir_hint and _safe_run_dir(run_dir_hint):
        run_dir = Path(run_dir_hint)
    else:
        run_dir = _default_run_dir(task_id)

    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    running_state["run_dir"] = str(run_dir)
    write_state(running_task, running_state)

    _write_json(artifacts_dir / "agent_task.json", task)

    pre_cmds, post_cmds = _task_validate(task)
    if pre_cmds:
        ok_pre, err_pre = _run_commands(pre_cmds, logs_dir / "agent_validate_pre.log")
        if not ok_pre:
            artifacts = {
                "agent_task": str(artifacts_dir / "agent_task.json"),
                "validate_pre_log": str(logs_dir / "agent_validate_pre.log"),
            }
            return finalize(False, run_dir, err_pre, artifacts)

    try:
        registry = AdapterRegistry()
        runner_result = run_plan(plan, run_dir, registry)
    except Exception as exc:
        artifacts = {"agent_task": str(artifacts_dir / "agent_task.json")}
        return finalize(False, run_dir, f"runner execution failed: {exc}", artifacts)

    if post_cmds:
        ok_post, err_post = _run_commands(post_cmds, logs_dir / "agent_validate_post.log")
        if not ok_post:
            artifacts = {
                "agent_task": str(artifacts_dir / "agent_task.json"),
                "run_plan": str(artifacts_dir / "run_plan.json"),
                "result": str(artifacts_dir / "result.json"),
                "validate_post_log": str(logs_dir / "agent_validate_post.log"),
            }
            return finalize(False, run_dir, err_post, artifacts)

    runner_ok = bool(runner_result.get("ok", False)) if isinstance(runner_result, dict) else False
    error_summary = ""
    if not runner_ok:
        error_summary = str(runner_result.get("error_summary", "runner reported failure")) if isinstance(runner_result, dict) else "runner reported failure"

    artifacts = {
        "agent_task": str(artifacts_dir / "agent_task.json"),
        "run_plan": str(artifacts_dir / "run_plan.json"),
        "result": str(artifacts_dir / "result.json"),
    }
    return finalize(runner_ok, run_dir, error_summary, artifacts)


def run_sweep(queue_path: str | Path, max_tasks: Optional[int] = None, verbose: bool = False) -> int:
    queue_root = Path(queue_path)
    ensure_queue_layout(queue_root)
    report_root = _repo_root() / "reports"
    report_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    while True:
        tasks = list_inbox_tasks(queue_root)
        if not tasks:
            break
        task_path = tasks[0]
        _process_task_file(task_path, queue_root, report_root, verbose=verbose)
        processed += 1
        if max_tasks is not None and processed >= max_tasks:
            break
    return processed


def main() -> int:
    parser = argparse.ArgumentParser(prog="ael.agent")
    parser.add_argument("--queue", default="queue", help="Queue root path")
    parser.add_argument("--poll", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one sweep and exit")
    parser.add_argument("--max-tasks", type=int, default=None, help="Optional max tasks to process")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.once:
        run_sweep(args.queue, max_tasks=args.max_tasks, verbose=args.verbose)
        return 0

    while True:
        run_sweep(args.queue, max_tasks=args.max_tasks, verbose=args.verbose)
        time.sleep(max(0.1, float(args.poll)))


if __name__ == "__main__":
    raise SystemExit(main())
