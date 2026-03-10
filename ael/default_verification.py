from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ael import paths as ael_paths
from ael import strategy_resolver
from ael.config_resolver import resolve_probe_config, resolve_probe_instance
from ael.adapters import preflight
from ael.instruments import provision as instrument_provision
from ael.pipeline import _normalize_probe_cfg, _simple_yaml_load, run_pipeline
from ael.probe_binding import load_probe_binding


DEFAULT_CONFIG_PATH = ael_paths.repo_root() / "configs" / "default_verification_setting.yaml"


def _default_payload() -> Dict[str, Any]:
    return {"version": 1, "mode": "none"}


def _load_text_payload(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    # JSON is a YAML subset and keeps parsing deterministic without extra deps.
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_payload(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_setting(path: str | None = None) -> Dict[str, Any]:
    cfg = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg.exists():
        return _default_payload()
    loaded = _load_text_payload(cfg)
    if not isinstance(loaded, dict):
        return _default_payload()
    out = dict(_default_payload())
    out.update(loaded)
    return out


def save_setting(payload: Dict[str, Any], path: str | None = None) -> None:
    cfg = Path(path) if path else DEFAULT_CONFIG_PATH
    _save_payload(cfg, payload)


def preset_payload(name: str) -> Dict[str, Any]:
    key = str(name or "").strip().lower()
    if key == "none":
        return {"version": 1, "mode": "none"}
    if key == "preflight_only":
        return {
            "version": 1,
            "mode": "preflight_only",
            "instrument_instance": "esp32jtag_stm32_golden",
        }
    if key in ("rp2040_only", "rp2040_esp32jtag_only"):
        return {
            "version": 1,
            "mode": "single_run",
            "board": "rp2040_pico",
            "test": "tests/plans/gpio_signature.json",
            "instrument_instance": "esp32jtag_rp2040_lab",
        }
    if key in ("esp32s3_then_rp2040", "esp32s3_gpio_then_rp2040"):
        return {
            "version": 1,
            "mode": "sequence",
            "execution_policy": {"kind": "serial"},
            "stop_on_fail": True,
            "steps": [
                {
                    "name": "esp32s3_golden_gpio",
                    "board": "esp32s3_devkit",
                    "test": "tests/plans/esp32s3_gpio_signature_with_meter.json",
                    "instrument_instance": "esp32jtag_stm32_golden",
                },
                {
                    "name": "rp2040_golden_gpio_signature",
                    "board": "rp2040_pico",
                    "test": "tests/plans/gpio_signature.json",
                    "instrument_instance": "esp32jtag_rp2040_lab",
                },
            ],
        }
    raise ValueError(f"unknown preset: {name}")


def _resolve_path(repo_root: Path, value: str | None, default: str | None = None) -> str | None:
    raw = str(value or default or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str((repo_root / p).resolve())


def _resolve_step_probe_binding(repo_root: Path, step: Dict[str, Any]) -> Tuple[Dict[str, Any], str | None]:
    config_root = repo_root if (repo_root / "configs").exists() else ael_paths.repo_root()
    instance_id = str(step.get("instrument_instance") or "").strip() or resolve_probe_instance(
        str(config_root),
        args=None,
        board_id=str(step.get("board") or ""),
    )
    probe_path = _resolve_path(
        config_root,
        step.get("probe"),
        resolve_probe_config(str(config_root), args=None, board_id=str(step.get("board") or "")),
    )
    binding = load_probe_binding(
        config_root,
        probe_path=None if instance_id else probe_path,
        instance_id=instance_id or None,
    )
    if binding.legacy_warning:
        print(f"default_verification: {binding.legacy_warning}")
    return binding.raw, binding.config_path


def _run_preflight_only(repo_root: Path, step: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    probe_raw, _probe_path = _resolve_step_probe_binding(repo_root, step)
    probe_cfg = _normalize_probe_cfg(probe_raw)
    ok, info = preflight.run(probe_cfg)
    return (0 if ok else 2), {"ok": bool(ok), "result": info or {}}


def _resolve_board_raw(repo_root: Path, board: str | None) -> Dict[str, Any]:
    board_id = str(board or "").strip()
    if not board_id:
        return {}
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not board_path.exists():
        return {}
    loaded = _simple_yaml_load(str(board_path))
    return loaded if isinstance(loaded, dict) else {}


def _ensure_step_meter_reachable(repo_root: Path, board: str | None, test_path: str | None) -> None:
    if not test_path:
        return
    test_raw = _load_text_payload(Path(test_path))
    if not isinstance(test_raw, dict):
        return
    board_raw = _resolve_board_raw(repo_root, board)
    board_cfg = board_raw.get("board", {}) if isinstance(board_raw.get("board"), dict) else {}
    if not strategy_resolver.is_meter_digital_verify_test(test_raw, board_cfg):
        return
    instrument_id, tcp_cfg, manifest = strategy_resolver.resolve_instrument_context(test_raw, board_cfg)
    if str(instrument_id or "").strip() != "esp32s3_dev_c_meter":
        return
    manifest_payload = dict(manifest) if isinstance(manifest, dict) else {}
    manifest_payload.setdefault("id", instrument_id)
    wifi_cfg = manifest_payload.get("wifi") if isinstance(manifest_payload.get("wifi"), dict) else {}
    if not wifi_cfg:
        wifi_cfg = {}
    if tcp_cfg.get("host") and "ap_ip" not in wifi_cfg:
        wifi_cfg["ap_ip"] = tcp_cfg.get("host")
    manifest_payload["wifi"] = wifi_cfg
    instrument_provision.ensure_meter_reachable(
        manifest=manifest_payload,
        host=tcp_cfg.get("host"),
    )


def _run_single(repo_root: Path, step: Dict[str, Any], output_mode: str) -> Tuple[int, Dict[str, Any]]:
    board = step.get("board")
    test = _resolve_path(repo_root, step.get("test"))
    if not board or not test:
        return 2, {"ok": False, "error": "single_run requires board and test"}
    _probe_raw, probe = _resolve_step_probe_binding(repo_root, step)
    try:
        _ensure_step_meter_reachable(repo_root, str(board), test)
    except Exception as exc:
        print(f"default_verification: {exc}")
        return 2, {"ok": False, "error": str(exc)}
    code = run_pipeline(
        probe_path=probe,
        board_arg=str(board),
        test_path=str(test),
        wiring=None,
        output_mode=output_mode,
    )
    return int(code), {"ok": int(code) == 0}


def _normalized_step(setting: Dict[str, Any], raw_step: Dict[str, Any], idx: int) -> Dict[str, Any]:
    step = dict(raw_step) if isinstance(raw_step, dict) else {}
    if not step.get("probe") and setting.get("probe"):
        step["probe"] = setting.get("probe")
    if not step.get("instrument_instance") and setting.get("instrument_instance"):
        step["instrument_instance"] = setting.get("instrument_instance")
    step["name"] = str(step.get("name") or f"step_{idx:02d}")
    step["action"] = str(step.get("action") or "single_run").strip().lower()
    return step


def _execution_policy(setting: Dict[str, Any]) -> Dict[str, Any]:
    raw = setting.get("execution_policy", {}) if isinstance(setting.get("execution_policy"), dict) else {}
    kind = str(raw.get("kind") or "parallel").strip().lower()
    if kind not in ("parallel", "serial"):
        kind = "parallel"
    return {"kind": kind}


def _log_line(lock: threading.Lock, message: str) -> None:
    with lock:
        print(message, flush=True)


def _run_step_action(repo_root: Path, step: Dict[str, Any], output_mode: str) -> Tuple[int, Dict[str, Any]]:
    if str(step.get("action") or "single_run").strip().lower() == "preflight_only":
        return _run_preflight_only(repo_root, step)
    return _run_single(repo_root, step, output_mode)


def _run_worker_iterations(
    repo_root: Path,
    step: Dict[str, Any],
    output_mode: str,
    max_iterations: int,
    stop_after_failure: bool,
    log_lock: threading.Lock,
) -> Dict[str, Any]:
    worker_name = str(step.get("name") or "worker")
    board = str(step.get("board") or "").strip()
    action = str(step.get("action") or "single_run").strip().lower()
    iterations: List[Dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        label = f"{worker_name} iteration {iteration}" if max_iterations > 1 else worker_name
        _log_line(log_lock, f"[START] {label}")
        started = time.monotonic()
        try:
            code, result = _run_step_action(repo_root, step, output_mode)
        except Exception as exc:
            code, result = 1, {"ok": False, "error": str(exc)}
        elapsed = round(time.monotonic() - started, 3)
        ok = code == 0
        record = {
            "name": worker_name,
            "board": board,
            "action": action,
            "iteration": iteration,
            "code": int(code),
            "ok": ok,
            "elapsed_s": elapsed,
            "result": result,
        }
        iterations.append(record)
        status = "PASS" if ok else "FAIL"
        _log_line(log_lock, f"[DONE] {label} {status} ({elapsed:.3f}s)")
        if not ok:
            reason = ""
            if isinstance(result, dict):
                reason = str(result.get("error") or result.get("error_summary") or "").strip()
            if reason:
                _log_line(log_lock, f"[FAIL] {label} {reason}")
            if stop_after_failure:
                break

    pass_count = sum(1 for item in iterations if item["ok"])
    fail_count = len(iterations) - pass_count
    return {
        "name": worker_name,
        "board": board,
        "requested_iterations": max_iterations,
        "completed_iterations": len(iterations),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "ok": fail_count == 0 and len(iterations) == max_iterations,
        "results": iterations,
    }


def _print_worker_totals(lock: threading.Lock, workers: List[Dict[str, Any]]) -> None:
    _log_line(lock, "[SUMMARY]")
    for worker in workers:
        _log_line(
            lock,
            f"{worker.get('name')}: {worker.get('pass_count', 0)}/{worker.get('completed_iterations', 0)} PASS",
        )


def _run_parallel_suite_once(
    repo_root: Path,
    steps: List[Dict[str, Any]],
    output_mode: str,
) -> Tuple[int, Dict[str, Any]]:
    log_lock = threading.Lock()
    workers: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(steps))) as executor:
        futures = [
            executor.submit(_run_worker_iterations, repo_root, step, output_mode, 1, False, log_lock)
            for step in steps
        ]
        for future in concurrent.futures.as_completed(futures):
            workers.append(future.result())

    _print_worker_totals(log_lock, workers)
    results = [item for worker in workers for item in worker.get("results", [])]
    failed = next((item for item in results if not bool(item.get("ok", False))), None)
    code = int(failed.get("code", 0)) if isinstance(failed, dict) else 0
    ok = failed is None
    return code, {
        "ok": ok,
        "mode": "sequence",
        "suite": {"steps": [step.get("name") for step in steps]},
        "execution_policy": {"kind": "parallel", "iterations_per_worker": 1},
        "workers": workers,
        "results": results,
    }


def _run_serial_suite_once(
    repo_root: Path,
    setting: Dict[str, Any],
    steps: List[Dict[str, Any]],
    output_mode: str,
) -> Tuple[int, Dict[str, Any]]:
    stop_on_fail = bool(setting.get("stop_on_fail", True))
    overall_ok = True
    last_code = 0
    results: List[Dict[str, Any]] = []

    for step in steps:
        code, result = _run_step_action(repo_root, step, output_mode)
        ok = code == 0
        results.append({"name": step["name"], "code": code, "ok": ok, "result": result})
        if not ok:
            overall_ok = False
            last_code = code
            if stop_on_fail:
                break

    return (0 if overall_ok else last_code or 1), {
        "ok": overall_ok,
        "mode": "sequence",
        "suite": {"steps": [step.get("name") for step in steps]},
        "execution_policy": {"kind": "serial", "iterations_per_worker": 1},
        "results": results,
    }


def _run_parallel_repeat_until_fail(
    repo_root: Path,
    steps: List[Dict[str, Any]],
    output_mode: str,
    limit: int,
) -> Tuple[int, Dict[str, Any]]:
    log_lock = threading.Lock()
    workers: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(steps))) as executor:
        futures = [
            executor.submit(_run_worker_iterations, repo_root, step, output_mode, limit, True, log_lock)
            for step in steps
        ]
        for future in concurrent.futures.as_completed(futures):
            workers.append(future.result())

    _print_worker_totals(log_lock, workers)
    results = [item for worker in workers for item in worker.get("results", [])]
    failures = [item for item in results if not bool(item.get("ok", False))]
    first_failure = failures[0] if failures else None
    code = int(first_failure.get("code", 0)) if isinstance(first_failure, dict) else 0
    ok = first_failure is None
    payload: Dict[str, Any] = {
        "ok": ok,
        "mode": "repeat_until_fail",
        "suite": {"steps": [step.get("name") for step in steps]},
        "execution_policy": {"kind": "parallel", "iterations_per_worker": limit, "stop_each_worker_on_failure": True},
        "requested_iterations_per_worker": limit,
        "workers": workers,
        "results": results,
    }
    if first_failure is not None:
        payload["failure"] = {
            "step_name": first_failure.get("name"),
            "board": first_failure.get("board"),
            "iteration": first_failure.get("iteration"),
            "step_code": first_failure.get("code"),
            "reason": (
                first_failure.get("result", {}).get("error")
                if isinstance(first_failure.get("result"), dict)
                else "step failed"
            )
            or "step failed",
        }
    return code, payload


def _detect_docs_only_changes(mode: str = "changed") -> bool:
    if mode not in ("changed", "staged"):
        return False
    cmd = ["git", "diff", "--name-only"]
    if mode == "staged":
        cmd.append("--cached")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ael_paths.repo_root()))
    except Exception:
        return False
    if res.returncode != 0:
        return False
    files = [ln.strip() for ln in (res.stdout or "").splitlines() if ln.strip()]
    if not files:
        return False
    return all(f.startswith("docs/") for f in files)


def run_default_setting(
    path: str | None = None,
    output_mode: str = "normal",
    skip_if_docs_only: bool = False,
    docs_check_mode: str = "changed",
) -> Tuple[int, Dict[str, Any]]:
    if skip_if_docs_only and _detect_docs_only_changes(docs_check_mode):
        print("default_verification: docs-only changes detected, skipping checks")
        return 0, {"ok": True, "skipped": "docs_only"}

    repo_root = ael_paths.repo_root()
    setting = load_setting(path)
    mode = str(setting.get("mode", "none")).strip().lower()
    results: List[Dict[str, Any]] = []

    if mode == "none":
        print("default_verification: mode=none (no checks)")
        return 0, {"ok": True, "mode": mode, "results": results}

    if mode == "preflight_only":
        code, result = _run_preflight_only(repo_root, setting)
        results.append({"name": "preflight_only", "code": code, "ok": code == 0, "result": result})
        return code, {"ok": code == 0, "mode": mode, "results": results}

    if mode == "single_run":
        code, result = _run_single(repo_root, setting, output_mode)
        results.append({"name": "single_run", "code": code, "ok": code == 0, "result": result})
        return code, {"ok": code == 0, "mode": mode, "results": results}

    if mode == "sequence":
        steps = setting.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return 2, {"ok": False, "mode": mode, "error": "sequence mode requires non-empty steps"}
        normalized_steps = [_normalized_step(setting, raw_step, idx) for idx, raw_step in enumerate(steps, start=1)]
        policy = _execution_policy(setting)
        if policy["kind"] == "serial":
            return _run_serial_suite_once(repo_root, setting, normalized_steps, output_mode)
        return _run_parallel_suite_once(repo_root, normalized_steps, output_mode)

    return 2, {"ok": False, "mode": mode, "error": f"unsupported mode: {mode}"}


def _first_failed_step(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(results, list):
        return None
    for item in results:
        if isinstance(item, dict) and not bool(item.get("ok", False)):
            return item
    return None


def _failure_summary(payload: Dict[str, Any], code: int) -> Dict[str, Any]:
    failed = _first_failed_step(payload)
    summary: Dict[str, Any] = {"code": int(code)}
    if failed is None:
        return summary
    summary["step_name"] = failed.get("name")
    summary["step_code"] = failed.get("code")
    result = failed.get("result", {}) if isinstance(failed.get("result"), dict) else {}
    error = str(result.get("error") or "").strip()
    if error:
        summary["reason"] = error
        return summary
    summary["reason"] = result.get("error_summary") or payload.get("error") or "step failed"
    return summary


def run_until_fail(
    limit: int,
    path: str | None = None,
    output_mode: str = "normal",
    skip_if_docs_only: bool = False,
    docs_check_mode: str = "changed",
) -> Tuple[int, Dict[str, Any]]:
    setting = load_setting(path)
    mode = str(setting.get("mode", "none")).strip().lower()
    if mode == "sequence":
        steps = setting.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return 2, {"ok": False, "mode": mode, "error": "sequence mode requires non-empty steps"}
        policy = _execution_policy(setting)
        if policy["kind"] != "serial":
            repo_root = ael_paths.repo_root()
            normalized_steps = [_normalized_step(setting, raw_step, idx) for idx, raw_step in enumerate(steps, start=1)]
            return _run_parallel_repeat_until_fail(
                repo_root=repo_root,
                steps=normalized_steps,
                output_mode=output_mode,
                limit=max(1, int(limit)),
            )

    max_runs = max(1, int(limit))
    runs: List[Dict[str, Any]] = []
    for idx in range(1, max_runs + 1):
        code, payload = run_default_setting(
            path=path,
            output_mode=output_mode,
            skip_if_docs_only=skip_if_docs_only,
            docs_check_mode=docs_check_mode,
        )
        run_record = {
            "iteration": idx,
            "code": int(code),
            "ok": int(code) == 0,
            "payload": payload,
        }
        runs.append(run_record)
        if code != 0:
            summary = _failure_summary(payload, code)
            print(
                f"default_verification: stopped on run {idx}/{max_runs}; "
                f"failed step={summary.get('step_name', 'unknown')} code={summary.get('step_code', code)}"
            )
            reason = str(summary.get("reason") or "").strip()
            if reason:
                print(f"default_verification: failure reason: {reason}")
            return code, {
                "ok": False,
                "mode": "repeat_until_fail",
                "requested_runs": max_runs,
                "completed_runs": idx,
                "runs": runs,
                "failure": summary,
            }
    return 0, {
        "ok": True,
        "mode": "repeat_until_fail",
        "requested_runs": max_runs,
        "completed_runs": max_runs,
        "runs": runs,
    }
