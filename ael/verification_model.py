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
        "serial_ports": [],
        "instrument_endpoints": [],
        "other": [],
    }
    for key in raw:
        text = str(key or "").strip()
        if not text:
            continue
        if text.startswith("dut:"):
            summary["dut_ids"].append(text.split(":", 1)[1])
        elif text.startswith("probe:"):
            summary["control_instrument_endpoints"].append(text.split(":", 1)[1])
        elif text.startswith("probe_path:"):
            summary["control_instrument_configs"].append(text.split(":", 1)[1])
        elif text.startswith("serial:"):
            summary["serial_ports"].append(text.split(":", 1)[1])
        elif text.startswith("instrument:"):
            summary["instrument_endpoints"].append(text.split(":", 1)[1])
        else:
            summary["other"].append(text)
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


def summarize_worker_health(workers: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    condition_counts: Dict[str, int] = {}
    degraded_workers: List[Dict[str, Any]] = []
    for worker in list(workers or []):
        if not isinstance(worker, dict):
            continue
        results = worker.get("results")
        last = results[-1] if isinstance(results, list) and results else {}
        result = last.get("result") if isinstance(last, dict) else {}
        if not isinstance(result, dict):
            continue
        observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
        condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
        if not condition:
            continue
        condition_counts[condition] = condition_counts.get(condition, 0) + 1
        degraded_workers.append(
            {
                "name": worker.get("name"),
                "board": worker.get("board"),
                "instrument_condition": condition,
                "completed_iterations": worker.get("completed_iterations"),
                "requested_iterations": worker.get("requested_iterations"),
            }
        )
    return {
        "instrument_condition_counts": condition_counts,
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
