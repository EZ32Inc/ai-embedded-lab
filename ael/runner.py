from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ael.run_contract import RunTermination
from ael import failure_recovery


@dataclass
class RunContext:
    run_dir: Path
    artifacts_dir: Path
    logs_dir: Path

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.artifacts_dir = self.run_dir / "artifacts"
        self.logs_dir = self.run_dir / "logs"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _step_type(step: Dict[str, Any]) -> str:
    return str(step.get("type", "")).strip()


def _step_retry_class(step: Dict[str, Any]) -> str:
    kind = _step_type(step)
    if kind.startswith("build."):
        return "build"
    if kind.startswith("load."):
        return "load"
    if kind.startswith("run."):
        return "run"
    if kind.startswith("check."):
        return "check"
    if kind.startswith("preflight."):
        return "preflight"
    if kind.startswith("plan."):
        return "plan"
    return ""


def _plan_retry_map(plan: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    policy = plan.get("recovery_policy", {}) if isinstance(plan, dict) else {}
    if not isinstance(policy, dict):
        return out
    retries = policy.get("retries", {})
    if not isinstance(retries, dict):
        return out
    for key, value in retries.items():
        try:
            out[str(key).strip().lower()] = max(0, int(value))
        except Exception:
            continue
    return out


def _retry_budget(step: Dict[str, Any], plan_retries: Dict[str, int]) -> int:
    # 1) Explicit per-step override wins.
    if step.get("retry_budget") is not None:
        try:
            return max(0, int(step.get("retry_budget")))
        except Exception:
            return 0

    # 2) Plan policy retries by mapped class.
    retry_class = _step_retry_class(step)
    if retry_class:
        if retry_class == "load" and "load" not in plan_retries and "run" in plan_retries:
            return int(plan_retries["run"])
        if retry_class == "run" and "run" not in plan_retries and "load" in plan_retries:
            return int(plan_retries["load"])
        if retry_class in plan_retries:
            return int(plan_retries[retry_class])

    # 3) Backward-compatible defaults.
    if retry_class == "build":
        return 1
    if retry_class in ("load", "run"):
        return 2
    if retry_class == "check":
        return 2
    return 0


def _default_anchor(step: Dict[str, Any]) -> str:
    if isinstance(step.get("rewind_anchor"), str) and step.get("rewind_anchor").strip():
        return str(step.get("rewind_anchor")).strip()

    kind = _step_type(step)
    if kind.startswith("build."):
        return "build"
    if kind.startswith("load.") or kind.startswith("run."):
        return "load"
    if kind.startswith("check."):
        return "load"
    return "build"


def _summary_from_result(payload: Dict[str, Any]) -> str:
    text = str(payload.get("error_summary", "")).strip()
    if text:
        return text
    text = str(payload.get("error", "")).strip()
    if text:
        return text
    return "step failed"


def _escalate_anchor(summary: str, current_anchor: str) -> str:
    low = summary.lower()
    signals = ("missing artifact", "file not found", "invalid image")
    if any(s in low for s in signals):
        return "build"
    return current_anchor


def _find_anchor_index(steps: List[Dict[str, Any]], anchor: str) -> int:
    anchor = str(anchor or "").strip()
    if not anchor:
        return 0

    for idx, step in enumerate(steps):
        if str(step.get("name", "")).strip() == anchor:
            return idx

    for idx, step in enumerate(steps):
        kind = _step_type(step)
        if anchor == "build" and kind.startswith("build."):
            return idx
        if anchor == "load" and (kind.startswith("load.") or kind.startswith("run.")):
            return idx
        if anchor == "check" and kind.startswith("check."):
            return idx

    return 0


def _can_run_recovery(plan: Dict[str, Any], action_type: str) -> bool:
    policy = plan.get("recovery_policy", {})
    if not isinstance(policy, dict):
        return False
    if policy.get("enabled") is False:
        return False

    allowed = policy.get("allowed_actions")
    if allowed is None:
        return True
    if not isinstance(allowed, list):
        return False
    return action_type in [str(x) for x in allowed]


def _run_recovery(
    plan: Dict[str, Any],
    hint: Dict[str, Any],
    ctx: RunContext,
    registry: Any,
) -> Tuple[bool, Dict[str, Any]]:
    action_type = str(hint.get("action_type", "")).strip()
    if not action_type:
        return False, {"ok": False, "error_summary": "invalid recovery hint"}
    if not _can_run_recovery(plan, action_type):
        return False, {"ok": False, "error_summary": "recovery action not allowed"}

    action = {
        "type": action_type,
        "params": hint.get("params", {}),
        "reason": hint.get("reason", ""),
    }
    try:
        adapter = registry.recovery(action_type)
    except Exception as exc:
        return False, {"ok": False, "error_summary": f"recovery adapter lookup failed: {exc}"}

    try:
        out = adapter.execute(action, plan, ctx)
    except Exception as exc:
        return False, {"ok": False, "error_summary": f"recovery adapter execute failed: {exc}"}

    if not isinstance(out, dict):
        out = {"ok": False, "error_summary": "recovery adapter returned non-dict"}

    return bool(out.get("ok", False)), out


def run_plan(plan: dict, run_dir: Path, registry: Any) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("plan must be a dict")

    ctx = RunContext(Path(run_dir))
    _write_json(ctx.artifacts_dir / "run_plan.json", plan)

    started_at = _utc_now_iso()
    result: Dict[str, Any] = {
        "started_at": started_at,
        "finished_at": "",
        "ok": False,
        "termination": RunTermination.FAIL,
        "steps": [],
        "recovery": [],
        "error_summary": "",
    }

    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    plan_retries = _plan_retry_map(plan)
    timeout_s: Optional[float] = None
    timeout_raw = plan.get("timeout_s")
    if timeout_raw is not None:
        try:
            timeout_s = max(0.0, float(timeout_raw))
        except Exception:
            timeout_s = None
    result["timeout_s"] = timeout_s
    start_monotonic = time.monotonic()

    idx = 0
    guard = 0
    guard_limit = max(100, len(steps) * 20)

    while idx < len(steps):
        if timeout_s is not None and (time.monotonic() - start_monotonic) > timeout_s:
            result["error_summary"] = "run timeout reached"
            result["termination"] = RunTermination.TIMEOUT
            break
        guard += 1
        if guard > guard_limit:
            result["error_summary"] = "execution guard limit reached"
            result["termination"] = RunTermination.SAFETY_ABORT
            break

        step = steps[idx]
        if not isinstance(step, dict):
            result["error_summary"] = f"invalid step at index {idx}"
            break

        name = str(step.get("name") or f"step_{idx}")
        kind = _step_type(step)

        try:
            adapter = registry.get(kind)
        except Exception as exc:
            result["error_summary"] = f"adapter lookup failed for {kind}: {exc}"
            break

        budget = _retry_budget(step, plan_retries)
        attempt = 0
        step_ok = False
        step_last: Dict[str, Any] = {"ok": False, "error_summary": "not_run"}

        while attempt <= budget:
            if timeout_s is not None and (time.monotonic() - start_monotonic) > timeout_s:
                step_last = {"ok": False, "error_summary": "run timeout reached"}
                step_ok = False
                result["termination"] = RunTermination.TIMEOUT
                break
            attempt += 1
            try:
                out = adapter.execute(step, plan, ctx)
            except Exception as exc:
                out = {"ok": False, "error_summary": f"adapter execute failed: {exc}"}

            if not isinstance(out, dict):
                out = {"ok": False, "error_summary": "adapter returned non-dict"}

            step_last = out
            step_ok = bool(out.get("ok", False))
            result["steps"].append(
                {
                    "name": name,
                    "type": kind,
                    "attempt": attempt,
                    "effective_retry_budget": budget,
                    "ok": step_ok,
                    "result": out,
                }
            )

            if step_ok:
                idx += 1
                break

        if step_ok:
            continue

        summary = _summary_from_result(step_last)
        hint = failure_recovery.normalize_recovery_hint(step_last.get("recovery_hint"))
        failure_kind = failure_recovery.normalize_failure_kind(step_last.get("failure_kind"))

        if hint:
            rec_ok, rec_out = _run_recovery(plan, hint, ctx, registry)
            result["recovery"].append(
                {
                    "step": name,
                    "failure_kind": failure_kind,
                    "recovery_hint": hint,
                    "action_type": hint.get("action_type", ""),
                    "ok": rec_ok,
                    "result": rec_out,
                }
            )
            if rec_ok:
                anchor = _default_anchor(step)
                anchor = _escalate_anchor(summary, anchor)
                idx = _find_anchor_index(steps, anchor)
                continue

        result["error_summary"] = summary
        break

    result["ok"] = bool(idx >= len(steps) and not result.get("error_summary"))
    result["finished_at"] = _utc_now_iso()
    if result["ok"]:
        result["error_summary"] = ""
        result["termination"] = RunTermination.PASS
        result["failure_kind"] = ""
    elif result.get("termination") not in RunTermination.ALL:
        result["termination"] = RunTermination.FAIL
    if not result.get("ok"):
        if result.get("termination") == RunTermination.TIMEOUT:
            result["failure_kind"] = failure_recovery.FAILURE_TIMEOUT
        else:
            last_failure = failure_recovery.FAILURE_UNKNOWN
            for entry in reversed(result.get("steps", [])):
                if not isinstance(entry, dict):
                    continue
                out = entry.get("result", {})
                if not isinstance(out, dict):
                    continue
                kind = failure_recovery.normalize_failure_kind(out.get("failure_kind"))
                if kind != failure_recovery.FAILURE_UNKNOWN:
                    last_failure = kind
                    break
            result["failure_kind"] = last_failure

    _write_json(ctx.artifacts_dir / "result.json", result)
    return result
