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
from ael.bridge_task import is_bridge_task, noop_plan
from ael.codex_driver import CodexDriver
from ael.gates import run_gates
from ael.planner import generate_plan
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
from ael import paths as ael_paths


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
    return ael_paths.repo_root()


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


def _read_json(path: Path) -> Dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _task_validate(task: Dict) -> Tuple[List[str], List[str]]:
    validate = task.get("validate", {}) if isinstance(task.get("validate"), dict) else {}
    pre = validate.get("pre", []) if isinstance(validate.get("pre"), list) else []
    post = validate.get("post", []) if isinstance(validate.get("post"), list) else []
    pre_cmds = [str(x) for x in pre if isinstance(x, (str, int, float))]
    post_cmds = [str(x) for x in post if isinstance(x, (str, int, float))]
    return pre_cmds, post_cmds


def _task_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    return _write


def _bridge_run_plan(task: Dict) -> Tuple[Optional[Dict], str]:
    kind = str(task.get("kind", "")).strip()
    payload = task.get("payload", {}) if isinstance(task.get("payload"), dict) else {}
    if kind == "noop":
        return noop_plan(task), ""
    if kind == "runplan":
        runplan = payload.get("runplan")
        if isinstance(runplan, dict):
            return runplan, ""
        test = str(payload.get("test", "general")).strip() or "general"
        board = str(payload.get("board", "")).strip()
        note = f"{test} test {board}".strip()
        return {
            "version": "runplan/0.1",
            "plan_id": f"bridge_runplan_{test}",
            "created_at": _now_iso(),
            "inputs": {"test": test, "board": board},
            "selected": {"test_config": "bridge/runplan_noop"},
            "context": {},
            "steps": [
                {
                    "name": "check_bridge_runplan",
                    "type": "check.noop",
                    "inputs": {"note": note or "bridge runplan"},
                }
            ],
            "recovery_policy": {"enabled": False},
            "meta": {},
        }, ""
    return None, ""


def _execute_bridge_subtask(subtask: Dict, run_dir: Path, tasklog) -> Tuple[bool, str, Dict[str, str]]:
    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    _write_json(artifacts_dir / "task.json", subtask)

    kind = str(subtask.get("kind", "")).strip()
    payload = subtask.get("payload", {}) if isinstance(subtask.get("payload"), dict) else {}
    exec_mode = str(payload.get("execution_mode", "")).strip()
    downgrade_reason = str(payload.get("downgrade_reason", "")).strip()
    if kind == "codex":
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return False, "bridge codex subtask missing prompt", {"task": str(artifacts_dir / "task.json")}
        repo_root = str(payload.get("repo_root", "."))
        timeout_s = int(payload.get("timeout_s", 1800))
        transcript_path = artifacts_dir / "codex_transcript.log"
        tasklog(f"subtask codex start: {subtask.get('title', '')}")
        codex = CodexDriver()
        codex_out = codex.run(repo_root=repo_root, prompt=prompt, timeout_s=timeout_s, log_path=str(transcript_path))
        _write_json(artifacts_dir / "codex_result.json", codex_out)
        _write_json(
            run_dir / "result.json",
            {
                "ok": bool(codex_out.get("ok", False)),
                "kind": kind,
                "title": subtask.get("title", ""),
                "error_summary": str(codex_out.get("error_summary", "")),
                "execution_mode": "codex" if bool(codex_out.get("ok", False)) else (exec_mode or "offline"),
                "downgrade_reason": downgrade_reason or ("codex_disabled" if "disabled" in str(codex_out.get("error_summary", "")).lower() else ""),
            },
        )
        return bool(codex_out.get("ok", False)), str(codex_out.get("error_summary", "")), {
            "task": str(artifacts_dir / "task.json"),
            "codex_result": str(artifacts_dir / "codex_result.json"),
            "codex_transcript": str(transcript_path),
        }

    plan, plan_err = _bridge_run_plan(subtask)
    if not plan:
        return False, plan_err or "subtask plan resolution failed", {"task": str(artifacts_dir / "task.json")}

    tasklog(f"subtask runner start: {subtask.get('title', '')}")
    try:
        registry = AdapterRegistry()
        runner_result = run_plan(plan, run_dir, registry)
    except Exception as exc:
        return False, f"subtask runner exception: {exc}", {"task": str(artifacts_dir / "task.json")}
    ok = bool(runner_result.get("ok", False))
    err = "" if ok else str(runner_result.get("error_summary", "runner reported failure"))
    _write_json(
        run_dir / "result.json",
        {
            "ok": ok,
            "kind": kind,
            "title": subtask.get("title", ""),
            "error_summary": err,
            "execution_mode": exec_mode or ("noop" if kind == "noop" else "offline"),
            "downgrade_reason": downgrade_reason,
        },
    )
    artifacts = {
        "task": str(artifacts_dir / "task.json"),
        "run_plan": str(artifacts_dir / "run_plan.json"),
        "result": str(artifacts_dir / "result.json"),
    }
    return ok, err, artifacts


def _write_plan_report(report_root: Path, task_id: str, prompt: str, plan_items: List[Dict], results: List[Dict], run_dir: Path) -> Path:
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / f"plan_{task_id}.md"
    lines: List[str] = [
        "# AEL Plan Execution Report",
        "",
        f"- task_id: {task_id}",
        f"- prompt: {prompt}",
        f"- run_dir: {run_dir}",
        f"- execution_mode: {('codex' if any(str(r.get('execution_mode','')) == 'codex' for r in results) else 'offline')}",
        f"- downgrade_reason: {next((str(r.get('downgrade_reason','')) for r in results if str(r.get('downgrade_reason','')).strip()), '')}",
        "",
        "## Plan",
        "",
    ]
    for idx, item in enumerate(plan_items, start=1):
        lines.append(f"- {idx}. {item.get('title', '')} [{item.get('kind', '')}]")
    lines.extend(["", "## Execution Results", ""])
    for result in results:
        status = "success" if bool(result.get("ok", False)) else "failed"
        lines.append(f"- task{result.get('index')}: {status} ({result.get('title', '')})")
        lines.append(f"  - execution_mode: {result.get('execution_mode', '')}")
        lines.append(f"  - downgrade_reason: {result.get('downgrade_reason', '')}")
        if not bool(result.get("ok", False)):
            lines.append(f"  - error: {result.get('error_summary', '')}")
    lines.extend(["", "## Logs", ""])
    lines.append(f"- run_dir: {run_dir}")
    lines.append(f"- task_log: {run_dir / 'logs' / 'task.log'}")
    lines.append(f"- plan_json: {run_dir / 'plan.json'}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


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
        "execution_mode": "",
        "downgrade_reason": "",
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

    bridge_mode = is_bridge_task(task)

    task_version = str(task.get("task_version", "")).strip()
    is_api_task = isinstance(task.get("plan_file"), str) and bool(str(task.get("plan_file")).strip())
    if task_version not in ("", "agenttask/0.1", "taskapi/0.3") and not is_api_task and not bridge_mode:
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

    plan: Optional[Dict] = None
    plan_err = ""
    run_dir_hint = None
    if bridge_mode:
        kind = str(task.get("kind", "")).strip()
        payload = task.get("payload", {}) if isinstance(task.get("payload"), dict) else {}
        if kind == "runplan":
            if isinstance(payload.get("run_dir"), str):
                run_dir_hint = str(payload.get("run_dir"))
            elif isinstance(task.get("run_dir_hint"), str):
                run_dir_hint = str(task.get("run_dir_hint"))
            if not run_dir_hint:
                run_dir_hint = str(queue_root / "running" / task_id)
        elif kind in ("noop", "codex"):
            run_dir_hint = str(queue_root / "running" / task_id)

        plan, plan_err = _bridge_run_plan(task)
    else:
        plan, plan_err = _load_plan(task, running_task.parent)
        if plan:
            meta = plan.get("meta", {}) if isinstance(plan.get("meta"), dict) else {}
            if isinstance(meta.get("run_dir"), str):
                run_dir_hint = meta.get("run_dir")
            if isinstance(task.get("run_dir_hint"), str) and task.get("run_dir_hint"):
                run_dir_hint = str(task.get("run_dir_hint"))

    if bridge_mode and str(task.get("kind", "")).strip() in ("codex", "plan"):
        pass
    elif not plan:
        return finalize(False, None, plan_err or "plan resolution failed", {})

    if run_dir_hint and _safe_run_dir(run_dir_hint):
        run_dir = Path(run_dir_hint)
    elif bridge_mode:
        run_dir = queue_root / "running" / task_id
    else:
        run_dir = _default_run_dir(task_id)

    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    running_state["run_dir"] = str(run_dir)
    write_state(running_task, running_state)
    task_log = logs_dir / "task.log"
    tasklog = _task_logger(task_log)
    tasklog("task claimed")
    tasklog(f"task_id={task_id}")
    if bridge_mode:
        tasklog(f"bridge kind={task.get('kind')}")

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

    runner_result: Dict = {}
    kind = str(task.get("kind", "")).strip() if bridge_mode else ""
    exec_mode = "offline"
    downgrade_reason = ""
    plan_items: List[Dict] = []
    sub_results: List[Dict] = []
    plan_prompt = ""
    if bridge_mode and kind == "plan":
        payload = task.get("payload", {}) if isinstance(task.get("payload"), dict) else {}
        prompt = str(payload.get("prompt", "")).strip()
        plan_prompt = prompt
        if not prompt:
            artifacts = {"agent_task": str(artifacts_dir / "agent_task.json"), "task_log": str(task_log)}
            return finalize(False, run_dir, "bridge plan task missing payload.prompt", artifacts)

        tasklog("plan generation started")
        plan_items = generate_plan(prompt)
        _write_json(run_dir / "plan.json", {"task_id": task_id, "prompt": prompt, "tasks": plan_items})
        tasklog(f"plan generation completed: {len(plan_items)} subtasks")

        tasks_root = run_dir / "tasks"
        tasks_root.mkdir(parents=True, exist_ok=True)
        overall_ok = True
        overall_err = ""
        for idx, subtask in enumerate(plan_items, start=1):
            sub_title = str(subtask.get("title", f"task_{idx}"))
            sub_dir = tasks_root / f"{idx:02d}_{_slugify(sub_title)}"
            ok_sub, err_sub, sub_artifacts = _execute_bridge_subtask(subtask, sub_dir, tasklog)
            sub_result = {
                "index": idx,
                "title": sub_title,
                "kind": str(subtask.get("kind", "")),
                "ok": ok_sub,
                "error_summary": err_sub,
                "run_dir": str(sub_dir),
                "artifacts": sub_artifacts,
                "execution_mode": str((_read_json(sub_dir / "result.json") or {}).get("execution_mode", "")),
                "downgrade_reason": str((_read_json(sub_dir / "result.json") or {}).get("downgrade_reason", "")),
            }
            _write_json(sub_dir / "result.json", sub_result)
            sub_results.append(sub_result)
            if not ok_sub:
                overall_ok = False
                overall_err = err_sub or f"subtask {idx} failed"
                break
        _write_json(artifacts_dir / "plan_results.json", {"ok": overall_ok, "tasks": sub_results, "error_summary": overall_err})
        runner_result = {"ok": overall_ok, "error_summary": overall_err, "plan_tasks": sub_results}
        exec_mode = "codex" if any(str(r.get("execution_mode", "")).strip() == "codex" for r in sub_results) else "offline"
        reasons = [str(r.get("downgrade_reason", "")).strip() for r in sub_results if str(r.get("downgrade_reason", "")).strip()]
        downgrade_reason = reasons[0] if reasons else ""
    elif bridge_mode and kind == "codex":
        payload = task.get("payload", {}) if isinstance(task.get("payload"), dict) else {}
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            artifacts = {"agent_task": str(artifacts_dir / "agent_task.json"), "task_log": str(task_log)}
            return finalize(False, run_dir, "bridge codex task missing payload.prompt", artifacts)
        repo_root = str(payload.get("repo_root", "."))
        timeout_s = int(payload.get("timeout_s", 1800))
        transcript_path = artifacts_dir / "codex_transcript.log"
        tasklog("codex run started")
        codex = CodexDriver()
        codex_out = codex.run(
            repo_root=repo_root,
            prompt=prompt,
            timeout_s=timeout_s,
            log_path=str(transcript_path),
        )
        _write_json(artifacts_dir / "codex_result.json", codex_out)
        tasklog("codex run finished")
        runner_result = {"ok": bool(codex_out.get("ok", False)), "error_summary": str(codex_out.get("error_summary", ""))}
        if bool(codex_out.get("ok", False)):
            exec_mode = "codex"
            downgrade_reason = ""
        else:
            exec_mode = "offline"
            msg = str(codex_out.get("error_summary", ""))
            downgrade_reason = "codex_disabled" if "disabled" in msg.lower() else ""
    else:
        try:
            registry = AdapterRegistry()
            tasklog("runner started")
            runner_result = run_plan(plan, run_dir, registry)
            tasklog("runner finished")
            exec_mode = "noop" if (bridge_mode and kind == "noop") else "offline"
            downgrade_reason = "planner_fallback" if (bridge_mode and kind == "runplan") else ""
        except Exception as exc:
            artifacts = {"agent_task": str(artifacts_dir / "agent_task.json"), "task_log": str(task_log)}
            tasklog(f"runner exception: {exc}")
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
        "task_log": str(task_log),
    }
    run_plan_path = artifacts_dir / "run_plan.json"
    result_path = artifacts_dir / "result.json"
    if run_plan_path.exists():
        artifacts["run_plan"] = str(run_plan_path)
    if result_path.exists():
        artifacts["result"] = str(result_path)
    codex_result_path = artifacts_dir / "codex_result.json"
    codex_transcript_path = artifacts_dir / "codex_transcript.log"
    if codex_result_path.exists():
        artifacts["codex_result"] = str(codex_result_path)
    if codex_transcript_path.exists():
        artifacts["codex_transcript"] = str(codex_transcript_path)
    plan_json_path = run_dir / "plan.json"
    plan_results_path = artifacts_dir / "plan_results.json"
    if plan_json_path.exists():
        artifacts["plan"] = str(plan_json_path)
    if plan_results_path.exists():
        artifacts["plan_results"] = str(plan_results_path)
    if bridge_mode and kind == "plan":
        report_path = _write_plan_report(
            report_root=report_root,
            task_id=task_id,
            prompt=plan_prompt,
            plan_items=plan_items,
            results=sub_results,
            run_dir=run_dir,
        )
        artifacts["plan_report"] = str(report_path)

    result_json_path = artifacts_dir / "result.json"
    if result_json_path.exists():
        enriched = _read_json(result_json_path)
        enriched["execution_mode"] = exec_mode
        enriched["downgrade_reason"] = downgrade_reason
        _write_json(result_json_path, enriched)
    else:
        _write_json(
            result_json_path,
            {
                "ok": runner_ok,
                "error_summary": error_summary,
                "execution_mode": exec_mode,
                "downgrade_reason": downgrade_reason,
            },
        )
    running_state["execution_mode"] = exec_mode
    running_state["downgrade_reason"] = downgrade_reason
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


def execute_task_payload(
    task: Dict,
    queue_path: str | Path,
    report_root: str | Path,
    mode: Optional[_AgentMode] = None,
    task_index: int = 1,
    verbose: bool = False,
) -> Dict:
    queue_root = Path(queue_path)
    ensure_queue_layout(queue_root)
    report_root_path = Path(report_root)
    report_root_path.mkdir(parents=True, exist_ok=True)
    eff_mode = mode or _AgentMode(branch_worker=False, push=False, remote="origin", gates_path=None)

    task_id = str(task.get("task_id", "")).strip() if isinstance(task, dict) else ""
    if not task_id:
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + _slugify(str(task.get("title", "task")))
    payload = dict(task) if isinstance(task, dict) else {}
    payload["task_id"] = task_id

    inbox_path = queue_root / "inbox" / f"{task_id}__{_slugify(str(payload.get('title', 'task')))}.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    _process_task_file(
        inbox_path,
        queue_root,
        report_root_path,
        mode=eff_mode,
        task_index=int(task_index),
        verbose=verbose,
    )

    state_path = None
    status = "unknown"
    for state_name in ("done", "failed", "running", "inbox"):
        cand = queue_root / state_name / inbox_path.name.replace(".json", ".state.json")
        if cand.exists():
            state_path = cand
            status = state_name
            break
    state_payload = {}
    if state_path:
        try:
            state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state_payload = {}
    return {
        "task_id": task_id,
        "status": status,
        "state_path": str(state_path) if state_path else "",
        "state": state_payload,
    }


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
    parser.add_argument("--api", action="store_true", help="Start task API server mode")
    parser.add_argument("--api-host", default="127.0.0.1", help="Task API bind host")
    parser.add_argument("--api-port", type=int, default=8765, help="Task API bind port")
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

    if bool(args.api):
        from ael.task_api import run_server

        return run_server(
            host=str(args.api_host),
            port=int(args.api_port),
            queue_root=str(args.queue),
            report_root=str(args.report_root),
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
