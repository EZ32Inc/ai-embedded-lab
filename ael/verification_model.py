from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
import time

from ael import resource_locks


VerificationRunner = Callable[[Path, Dict[str, Any], str], Tuple[int, Dict[str, Any]]]
VerificationLogger = Callable[[str], None]


def summarize_resource_keys(keys: List[str] | None) -> Dict[str, Any]:
    raw = list(keys or [])
    summary: Dict[str, Any] = {
        "dut_ids": [],
        "control_instrument_endpoints": [],
        "control_instrument_configs": [],
        "controller_endpoints": [],
        "controller_configs": [],
        "serial_ports": [],
        "instrument_endpoints": [],
        "other": [],
    }
    def _append_unique(name: str, value: str) -> None:
        bucket = summary.setdefault(name, [])
        if value not in bucket:
            bucket.append(value)

    for key in raw:
        text = str(key or "").strip()
        if not text:
            continue
        if text.startswith("dut:"):
            _append_unique("dut_ids", text.split(":", 1)[1])
        elif text.startswith("probe:"):
            value = text.split(":", 1)[1]
            _append_unique("control_instrument_endpoints", value)
            _append_unique("controller_endpoints", value)
        elif text.startswith("probe_path:"):
            value = text.split(":", 1)[1]
            _append_unique("control_instrument_configs", value)
            _append_unique("controller_configs", value)
        elif text.startswith("controller:"):
            _append_unique("controller_endpoints", text.split(":", 1)[1])
        elif text.startswith("controller_path:"):
            _append_unique("controller_configs", text.split(":", 1)[1])
        elif text.startswith("serial:"):
            _append_unique("serial_ports", text.split(":", 1)[1])
        elif text.startswith("instrument:"):
            _append_unique("instrument_endpoints", text.split(":", 1)[1])
        else:
            _append_unique("other", text)
    return summary


def _failure_summary(result: Dict[str, Any] | Any) -> str:
    if not isinstance(result, dict):
        return ""
    parts: List[str] = []
    verify_substage = str(result.get("verify_substage") or "").strip()
    observations = result.get("observations")
    if not verify_substage and isinstance(observations, dict):
        verify_substage = str(observations.get("verify_substage") or "").strip()
    if verify_substage:
        parts.append(f"verify_substage={verify_substage}")

    failure_class = str(result.get("failure_class") or "").strip()
    if not failure_class and isinstance(observations, dict):
        failure_class = str(observations.get("failure_class") or "").strip()
    if failure_class:
        parts.append(f"failure_class={failure_class}")

    instrument_condition = str(result.get("instrument_condition") or "").strip()
    if not instrument_condition and isinstance(observations, dict):
        instrument_condition = str(observations.get("instrument_condition") or "").strip()
    if not instrument_condition:
        if failure_class == "network_meter_reachability":
            instrument_condition = "instrument_unreachable"
        elif failure_class == "network_meter_tcp":
            instrument_condition = "instrument_transport_unavailable"
        elif failure_class == "network_meter_api":
            instrument_condition = "instrument_api_unavailable"
        elif verify_substage == "instrument.signature" or failure_class.startswith("instrument_"):
            instrument_condition = "instrument_verify_failed"
    if instrument_condition:
        parts.append(f"instrument_condition={instrument_condition}")

    failure_scope = str(result.get("failure_scope") or "").strip()
    if not failure_scope and isinstance(observations, dict):
        failure_scope = str(observations.get("failure_scope") or "").strip()
    if not failure_scope:
        if instrument_condition in ("instrument_unreachable", "instrument_transport_unavailable", "instrument_api_unavailable"):
            failure_scope = "bench"
        elif instrument_condition == "instrument_verify_failed":
            failure_scope = "verify"
    if failure_scope:
        parts.append(f"failure_scope={failure_scope}")

    policy = result.get("degraded_instrument_policy")
    policy_class = str(policy.get("policy_class") or "").strip() if isinstance(policy, dict) else ""
    if not policy_class:
        if instrument_condition == "instrument_unreachable":
            policy_class = "bench_degraded_fail_fast"
        elif instrument_condition in ("instrument_transport_unavailable", "instrument_api_unavailable"):
            policy_class = "bench_degraded_retry_once"
        elif instrument_condition == "instrument_verify_failed":
            policy_class = "verify_no_retry"
    if policy_class:
        parts.append(f"policy_class={policy_class}")

    retry_summary = result.get("retry_summary")
    if isinstance(retry_summary, dict):
        meter_guard_attempts = retry_summary.get("meter_guard_attempts")
        if isinstance(meter_guard_attempts, int) and meter_guard_attempts > 0:
            parts.append(f"meter_guard_attempts={meter_guard_attempts}")

    error = str(result.get("error") or result.get("error_summary") or "").strip()
    if error:
        parts.append(f"error={error}")

    if isinstance(observations, dict):
        ping_ok = observations.get("ping", {}).get("ok") if isinstance(observations.get("ping"), dict) else None
        tcp_ok = observations.get("tcp", {}).get("ok") if isinstance(observations.get("tcp"), dict) else None
        api_ok = observations.get("api", {}).get("ok") if isinstance(observations.get("api"), dict) else None
        bench_bits = []
        if ping_ok is not None:
            bench_bits.append(f"ping={'ok' if ping_ok else 'fail'}")
        if tcp_ok is not None:
            bench_bits.append(f"tcp={'ok' if tcp_ok else 'fail'}")
        if api_ok is not None:
            bench_bits.append(f"api={'ok' if api_ok else 'fail'}")
        if bench_bits:
            parts.append("observations=" + ",".join(bench_bits))

    return " ".join(parts).strip()


def _infer_result_instrument_health(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    direct = str(result.get("instrument_health") or result.get("health") or "").strip()
    if direct:
        return direct
    if bool(result.get("ok")):
        return "ready"
    observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
    condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
    if condition in {"instrument_unreachable", "instrument_transport_unavailable", "instrument_api_unavailable", "instrument_verify_failed"}:
        return "degraded"
    return ""



def _infer_result_failure_boundary(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    direct = str(result.get("failure_boundary") or "").strip()
    if direct:
        return direct
    observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
    condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
    if condition == "instrument_unreachable":
        return "instrument_connectivity"
    if condition in {"instrument_transport_unavailable", "instrument_api_unavailable"}:
        return "instrument_service"
    if condition == "instrument_verify_failed":
        return "instrument_measurement"
    return ""



def _infer_result_recovery_hint(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    direct = str(result.get("recovery_hint") or "").strip()
    if direct:
        return direct
    policy = result.get("degraded_instrument_policy") if isinstance(result.get("degraded_instrument_policy"), dict) else {}
    policy_class = str(policy.get("policy_class") or "").strip()
    if not policy_class:
        observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
        condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
        if condition == "instrument_unreachable":
            policy_class = "bench_degraded_fail_fast"
        elif condition in {"instrument_transport_unavailable", "instrument_api_unavailable"}:
            policy_class = "bench_degraded_retry_once"
        elif condition == "instrument_verify_failed":
            policy_class = "verify_no_retry"
    if policy_class == "bench_degraded_fail_fast":
        return "restore instrument reachability before retrying the run"
    if policy_class == "bench_degraded_retry_once":
        return "recover instrument transport or API availability and retry once"
    if policy_class == "verify_no_retry":
        return "inspect instrument-side verification inputs before retrying"
    return ""


def summarize_worker_health(workers: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    condition_counts: Dict[str, int] = {}
    policy_counts: Dict[str, int] = {}
    failure_class_counts: Dict[str, int] = {}
    verify_substage_counts: Dict[str, int] = {}
    instrument_family_counts: Dict[str, int] = {}
    instrument_health_counts: Dict[str, int] = {}
    failure_boundary_counts: Dict[str, int] = {}
    recovery_hint_counts: Dict[str, int] = {}
    worker_pass_counts: Dict[str, int] = {}
    worker_fail_counts: Dict[str, int] = {}
    degraded_workers: List[Dict[str, Any]] = []
    total_pass_count = 0
    total_fail_count = 0
    for worker in list(workers or []):
        if not isinstance(worker, dict):
            continue
        name = str(worker.get("name") or "").strip()
        pass_count = int(worker.get("pass_count") or 0)
        fail_count = int(worker.get("fail_count") or 0)
        total_pass_count += pass_count
        total_fail_count += fail_count
        if name:
            worker_pass_counts[name] = pass_count
            worker_fail_counts[name] = fail_count
        results = worker.get("results")
        last = results[-1] if isinstance(results, list) and results else {}
        result = last.get("result") if isinstance(last, dict) else {}
        if not isinstance(result, dict):
            continue
        observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
        instrument_family = str(result.get("instrument_family") or result.get("instrument_interface_family") or "").strip()
        if instrument_family:
            instrument_family_counts[instrument_family] = instrument_family_counts.get(instrument_family, 0) + 1
        instrument_health = _infer_result_instrument_health(result)
        if instrument_health:
            instrument_health_counts[instrument_health] = instrument_health_counts.get(instrument_health, 0) + 1
        failure_boundary = _infer_result_failure_boundary(result)
        if failure_boundary:
            failure_boundary_counts[failure_boundary] = failure_boundary_counts.get(failure_boundary, 0) + 1
        recovery_hint = _infer_result_recovery_hint(result)
        if recovery_hint:
            recovery_hint_counts[recovery_hint] = recovery_hint_counts.get(recovery_hint, 0) + 1
        failure_class = str(result.get("failure_class") or observations.get("failure_class") or "").strip()
        if failure_class:
            failure_class_counts[failure_class] = failure_class_counts.get(failure_class, 0) + 1
        verify_substage = str(result.get("verify_substage") or observations.get("verify_substage") or "").strip()
        if verify_substage:
            verify_substage_counts[verify_substage] = verify_substage_counts.get(verify_substage, 0) + 1
        condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
        if not condition:
            continue
        condition_counts[condition] = condition_counts.get(condition, 0) + 1
        policy = result.get("degraded_instrument_policy") if isinstance(result.get("degraded_instrument_policy"), dict) else {}
        policy_class = str(policy.get("policy_class") or "").strip()
        if not policy_class:
            if condition == "instrument_unreachable":
                policy_class = "bench_degraded_fail_fast"
            elif condition in ("instrument_transport_unavailable", "instrument_api_unavailable"):
                policy_class = "bench_degraded_retry_once"
            elif condition == "instrument_verify_failed":
                policy_class = "verify_no_retry"
        if policy_class:
            policy_counts[policy_class] = policy_counts.get(policy_class, 0) + 1
        degraded_workers.append(
            {
                "name": worker.get("name"),
                "board": worker.get("board"),
                "instrument_condition": condition,
                "policy_class": policy_class or None,
                "completed_iterations": worker.get("completed_iterations"),
                "requested_iterations": worker.get("requested_iterations"),
            }
        )
    return {
        "total_workers": len(list(workers or [])),
        "total_pass_count": total_pass_count,
        "total_fail_count": total_fail_count,
        "worker_pass_counts": worker_pass_counts,
        "worker_fail_counts": worker_fail_counts,
        "instrument_condition_counts": condition_counts,
        "policy_class_counts": policy_counts,
        "failure_class_counts": failure_class_counts,
        "verify_substage_counts": verify_substage_counts,
        "instrument_family_counts": instrument_family_counts,
        "instrument_interface_family_counts": instrument_family_counts,
        "instrument_health_counts": instrument_health_counts,
        "failure_boundary_counts": failure_boundary_counts,
        "recovery_hint_counts": recovery_hint_counts,
        "degraded_workers": degraded_workers,
    }


@dataclass(frozen=True)
class VerificationTask:
    name: str
    board: str
    action: str = "single_run"
    config: Dict[str, Any] = field(default_factory=dict)

    def step(self) -> Dict[str, Any]:
        return {
            **dict(self.config),
            "name": self.name,
            "board": self.board,
            "action": self.action,
        }


@dataclass(frozen=True)
class VerificationSuite:
    name: str
    tasks: List[VerificationTask]
    execution_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationWorkerResult:
    name: str
    board: str
    requested_iterations: int
    completed_iterations: int
    pass_count: int
    fail_count: int
    ok: bool
    results: List[Dict[str, Any]]
    resource_keys: List[str]
    resource_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "board": self.board,
            "requested_iterations": self.requested_iterations,
            "completed_iterations": self.completed_iterations,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "ok": self.ok,
            "results": list(self.results),
            "resource_keys": list(self.resource_keys),
            "resource_summary": dict(self.resource_summary),
        }


@dataclass
class VerificationWorker:
    task: VerificationTask
    repo_root: Path
    output_mode: str
    runner: VerificationRunner
    iteration_limit: int = 1
    stop_after_failure: bool = False
    log_fn: VerificationLogger | None = None
    resource_keys: List[str] = field(default_factory=list)

    def run(self) -> VerificationWorkerResult:
        iterations: List[Dict[str, Any]] = []

        with resource_locks.claim(self.resource_keys, on_wait=self._log_wait):
            for iteration in range(1, self.iteration_limit + 1):
                label = self.task.name if self.iteration_limit == 1 else f"{self.task.name} iteration {iteration}"
                self._log(f"[START] {label}")
                started = time.monotonic()
                try:
                    code, result = self.runner(self.repo_root, self.task.step(), self.output_mode)
                except Exception as exc:
                    code, result = 1, {"ok": False, "error": str(exc)}
                elapsed = round(time.monotonic() - started, 3)
                ok = code == 0
                record = {
                    "name": self.task.name,
                    "board": self.task.board,
                    "action": self.task.action,
                    "iteration": iteration,
                    "code": int(code),
                    "ok": ok,
                    "elapsed_s": elapsed,
                    "result": result,
                }
                iterations.append(record)
                self._log(f"[DONE] {label} {'PASS' if ok else 'FAIL'} ({elapsed:.3f}s)")
                if not ok:
                    reason = _failure_summary(result)
                    if reason:
                        self._log(f"[FAIL] {label} {reason}")
                    if self.stop_after_failure:
                        break

        pass_count = sum(1 for item in iterations if item["ok"])
        fail_count = len(iterations) - pass_count
        return VerificationWorkerResult(
            name=self.task.name,
            board=self.task.board,
            requested_iterations=self.iteration_limit,
            completed_iterations=len(iterations),
            pass_count=pass_count,
            fail_count=fail_count,
            ok=fail_count == 0 and len(iterations) == self.iteration_limit,
            results=iterations,
            resource_keys=list(self.resource_keys),
            resource_summary=summarize_resource_keys(self.resource_keys),
        )

    def _log(self, message: str) -> None:
        if self.log_fn is not None:
            self.log_fn(message)

    def _log_wait(self, resource_key: str) -> None:
        self._log(f"[WAIT] {self.task.name} waiting for resource {resource_key}")
