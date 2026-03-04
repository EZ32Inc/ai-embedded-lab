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
from ael.gates import run_gates
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


class _AgentMode:
    def __init__(
        self,
        branch_worker: bool = False,
        push: bool = False,
        remote: str = "origin",
        gates_path: Optional[str] = None,
    ):
        self.branch_worker = bool(branch_worker)
        self.push = bool(push)
        self.remote = str(remote or "origin")
        self.gates_path = str(gates_path) if gates_path else None


def _now_iso() -> str:
    return datetime.now().isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    workdir = str(cwd or _repo_root())
    return subprocess.run(
        ["git", *cmd],
        cwd=workdir,
        capture_output=True,
        text=True,
    )


def _git_current_head() -> Tuple[Optional[str], str]:
    res = _git(["rev-parse", "HEAD"])
    if int(res.returncode) != 0:
        return None, (res.stderr or res.stdout or "git rev-parse failed").strip()
    return (res.stdout or "").strip(), ""


def _git_current_branch() -> Tuple[Optional[str], str]:
    res = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    if int(res.returncode) != 0:
        return None, (res.stderr or res.stdout or "git branch resolve failed").strip()
    return (res.stdout or "").strip(), ""


def _git_is_dirty() -> Tuple[Optional[bool], str]:
    res = _git(["status", "--porcelain"])
    if int(res.returncode) != 0:
        return None, (res.stderr or res.stdout or "git status failed").strip()
    return bool((res.stdout or "").strip()), ""


def _slugify(value: str) -> str:
    raw = (value or "").strip().lower()
    chars = []
    prev_dash = False
    for ch in raw:
        if ch.isalnum():
            chars.append(ch)
            prev_dash = False
            continue
        if not prev_dash:
            chars.append("-")
            prev_dash = True
    out = "".join(chars).strip("-")
    return out or "task"


def _task_branch_name(task_id: str, task_index: int) -> str:
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    return f"agent/{date_prefix}/task-{int(task_index):04d}-{_slugify(task_id)}"


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
    plan_file = task.get("plan_file")
    if not plan_path and isinstance(plan_file, str) and plan_file.strip():
        plan_path = plan_file
    if not plan_path:
        return None, "plan or plan_path is required"

    p = Path(str(plan_path))
    if not p.is_absolute():
        p_local = (task_dir / p).resolve()
        p_repo = (_repo_root() / p).resolve()
        if p_local.exists():
            p = p_local
        else:
            p = p_repo
    if not p.exists():
        return None, f"plan_path not found: {p}"
    # API tasks may point to non-JSON plan docs. We still execute through runner
    # with a no-op plan so queue ingestion and state transitions remain stable.
    if str(p.suffix).lower() != ".json":
        note = str(task.get("description", "")).strip() or f"plan_file={p}"
        plan = {
            "version": "runplan/0.1",
            "plan_id": str(task.get("task_id", "api-task")),
            "created_at": _now_iso(),
            "inputs": {
                "task_id": str(task.get("task_id", "")),
                "plan_file": str(p),
            },
            "selected": {"test_config": str(p)},
            "context": {},
            "steps": [
                {
                    "name": "check_api_task",
                    "type": "check.noop",
                    "inputs": {
                        "note": note,
                    },
                }
            ],
            "recovery_policy": {"enabled": False},
            "meta": {},
        }
        return plan, ""

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


def _process_task_file(
    task_inbox_path: Path,
    queue_root: Path,
    report_root: Path,
    mode: _AgentMode,
    task_index: int,
    verbose: bool = False,
) -> bool:
    running_task = claim_task(task_inbox_path, queue_root)
    started = time.monotonic()
    started_at = _now_iso()

    running_state: Dict[str, object] = {
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

    original_branch = ""

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
        if mode.branch_worker and original_branch:
            _git(["checkout", original_branch])
        return ok

    if not isinstance(task, dict):
        return finalize(False, None, "invalid task JSON", {})

    task_version = str(task.get("task_version", "")).strip()
    is_api_task = isinstance(task.get("plan_file"), str) and bool(str(task.get("plan_file")).strip())
    if task_version not in ("", "agenttask/0.1", "taskapi/0.3") and not is_api_task:
        return finalize(False, None, "unsupported task_version", {})

    if mode.branch_worker:
        branch_name = _task_branch_name(task_id, task_index)
        base_commit, commit_err = _git_current_head()
        if not base_commit:
            return finalize(False, None, f"git base commit read failed: {commit_err}", {})
        current_branch, branch_err = _git_current_branch()
        if not current_branch:
            return finalize(False, None, f"git current branch read failed: {branch_err}", {})
        original_branch = current_branch
        checkout = _git(["checkout", "-b", branch_name])
        if int(checkout.returncode) != 0:
            summary = (checkout.stderr or checkout.stdout or "git checkout -b failed").strip()
            return finalize(False, None, f"branch creation failed: {summary}", {})
        running_state["base_commit"] = base_commit
        running_state["branch_name"] = branch_name
        write_state(running_task, running_state)

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
    if mode.branch_worker:
        running_state["mode"] = "branch-worker"
        running_state["publish_requested"] = bool(mode.push)
        running_state["remote"] = mode.remote
        running_state["gates_path"] = mode.gates_path or ""
        gates_payload = run_gates(run_dir, gates_path=mode.gates_path)
        gates_json_path = artifacts_dir / "gates_result.json"
        _write_json(gates_json_path, gates_payload)
        artifacts["gates_result"] = str(gates_json_path)
        artifacts["gates_logs_dir"] = str(run_dir / "logs" / "gates")
        running_state["gate_results"] = gates_payload.get("results", [])
        running_state["gate_overall"] = gates_payload.get("overall", "fail")
        head_after, _ = _git_current_head()
        if head_after:
            running_state["final_commit"] = head_after

        gate_overall = str(gates_payload.get("overall", "FAIL")).upper()
        if gate_overall == "HUMAN_ACTION_REQUIRED":
            if not error_summary:
                error_summary = "HUMAN_ACTION_REQUIRED: hardware gate unavailable"
            running_state["disposition"] = "HUMAN_ACTION_REQUIRED"
            running_state["pushed"] = False
            return finalize(True, run_dir, error_summary, artifacts)
        if gate_overall == "SKIP":
            running_state["disposition"] = "SKIP"
            running_state["pushed"] = False
            return finalize(True, run_dir, "", artifacts)
        if gate_overall != "PASS":
            if not error_summary:
                error_summary = "mandatory gates failed"
            running_state["disposition"] = "FAILED"
            running_state["pushed"] = False
            return finalize(False, run_dir, error_summary, artifacts)
        if runner_ok:
            branch_name = str(running_state.get("branch_name", "")).strip()
            if mode.push and branch_name:
                push_cmd = ["push", mode.remote, branch_name]
                push_res = _git(push_cmd)
                push_log_path = run_dir / "logs" / "agent_push.log"
                push_log_path.write_text(
                    "$ git " + " ".join(push_cmd) + "\n"
                    + f"[exit_code] {push_res.returncode}\n\n"
                    + (push_res.stdout or "")
                    + ("\n" if push_res.stdout else "")
                    + (push_res.stderr or ""),
                    encoding="utf-8",
                )
                artifacts["push_log"] = str(push_log_path)
                if int(push_res.returncode) != 0:
                    running_state["disposition"] = "FAILED"
                    running_state["pushed"] = False
                    err_push = (push_res.stderr or push_res.stdout or "git push failed").strip()
                    return finalize(False, run_dir, f"push failed: {err_push}", artifacts)
                running_state["pushed"] = True
                running_state["remote_branch"] = f"{mode.remote}/{branch_name}"
            else:
                running_state["pushed"] = False
            running_state["disposition"] = "DONE"
            return finalize(True, run_dir, "", artifacts)
        running_state["disposition"] = "FAILED"
        running_state["pushed"] = False
        return finalize(False, run_dir, error_summary or "runner reported failure", artifacts)

    return finalize(runner_ok, run_dir, error_summary, artifacts)


def run_sweep(
    queue_path: str | Path,
    mode: _AgentMode,
    report_root: str | Path,
    max_tasks: Optional[int] = None,
    verbose: bool = False,
) -> int:
    queue_root = Path(queue_path)
    ensure_queue_layout(queue_root)
    report_root_path = Path(report_root)
    report_root_path.mkdir(parents=True, exist_ok=True)

    processed = 0
    while True:
        tasks = list_inbox_tasks(queue_root)
        if not tasks:
            break
        task_path = tasks[0]
        _process_task_file(
            task_path,
            queue_root,
            report_root_path,
            mode=mode,
            task_index=processed + 1,
            verbose=verbose,
        )
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
    parser.add_argument("--branch-worker", action="store_true", help="Enable branch-worker mode (v0.2)")
    parser.add_argument("--push", dest="push", action="store_true", default=None, help="Push branch on success")
    parser.add_argument("--no-push", dest="push", action="store_false", help="Do not push branch on success")
    parser.add_argument("--remote", default="origin", help="Remote name for push in branch-worker mode")
    parser.add_argument("--gates", default=None, help="Optional gate commands config path")
    parser.add_argument(
        "--report-root",
        default=os.environ.get("AEL_REPORT_ROOT") or str(_repo_root() / "reports"),
        help="Directory for nightly reports",
    )

    args = parser.parse_args()
    push_enabled = bool(args.push) if args.push is not None else bool(args.branch_worker)
    mode = _AgentMode(
        branch_worker=bool(args.branch_worker),
        push=push_enabled,
        remote=str(args.remote),
        gates_path=args.gates,
    )

    if mode.branch_worker:
        if os.environ.get("AEL_AGENT_ALLOW_DIRTY", "").strip() == "1":
            pass
        else:
            dirty, dirty_err = _git_is_dirty()
            if dirty is None:
                print(f"Agent: git check failed: {dirty_err}")
                return 2
            if dirty:
                print("Agent: refusing to start in branch-worker mode because working tree is dirty.")
                return 2

    if args.once:
        run_sweep(args.queue, mode=mode, report_root=args.report_root, max_tasks=args.max_tasks, verbose=args.verbose)
        return 0

    while True:
        run_sweep(args.queue, mode=mode, report_root=args.report_root, max_tasks=args.max_tasks, verbose=args.verbose)
        time.sleep(max(0.1, float(args.poll)))


if __name__ == "__main__":
    raise SystemExit(main())
