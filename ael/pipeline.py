import argparse
import json
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from ael.notifiers import discord_webhook
from ael import run_manager
from ael import paths as ael_paths
from ael import evidence as ael_evidence
from ael.adapter_registry import AdapterRegistry
from ael.runner import run_plan
from ael.run_contract import RunRequest, RunTermination
from ael import strategy_resolver

_REPO_ROOT = ael_paths.repo_root()


def _simple_yaml_load(path):
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        data = {}
        stack = [data]
        indent_stack = [0]
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip(" "))
                key, _, value = line.strip().partition(":")
                value = value.strip().strip('"')
                while indent < indent_stack[-1]:
                    stack.pop()
                    indent_stack.pop()
                if value == "":
                    obj = {}
                    stack[-1][key] = obj
                    stack.append(obj)
                    indent_stack.append(indent)
                else:
                    stack[-1][key] = value
        return data


def _deep_merge(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _normalize_probe_cfg(raw):
    return strategy_resolver.normalize_probe_cfg(raw)

def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info():
    info = {"commit": "", "dirty": False, "status": ""}
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            info["commit"] = (res.stdout or "").strip()

        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            status = (res.stdout or "").strip()
            info["status"] = status
            info["dirty"] = bool(status)
    except Exception:
        pass
    return info


def _write_json(path, data):
    try:
        run_manager.ensure_parent(Path(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except Exception:
        pass


def _copy_artifacts(firmware_path, artifacts_dir):
    if not firmware_path:
        return []
    copied = []
    base = Path(firmware_path)
    candidates = [base]
    candidates.append(base.with_suffix(".uf2"))
    candidates.append(base.with_suffix(".bin"))
    for p in candidates:
        if p.exists():
            dest = Path(artifacts_dir) / p.name
            try:
                dest.write_bytes(p.read_bytes())
                copied.append(str(dest))
            except Exception:
                pass
    return copied


@contextmanager
def _tee_output(log_path, output_mode):
    tee, f = run_manager.open_tee(Path(log_path), output_mode, console=sys.stdout)
    orig_out = sys.stdout
    orig_err = sys.stderr
    sys.stdout = tee
    sys.stderr = tee
    try:
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        sys.stdout = orig_out
        sys.stderr = orig_err
        f.close()


def _triage(stage, pre_info, uart_info=None, monitor_hint=None):
    print("FAIL: stage=" + stage)
    if stage == "preflight":
        if not pre_info.get("ping_ok"):
            print("Hint: probe not reachable. Check power and Wi-Fi/AP connection.")
        if not pre_info.get("tcp_ok"):
            print("Hint: debug port closed. Check debug server endpoint and IP/port.")
        if not pre_info.get("monitor_ok"):
            print("Hint: debug server connected but monitor failed. Try power-cycle target and probe.")
        if not pre_info.get("la_ok"):
            print("Hint: LA web API failed. Check web credentials and HTTPS settings.")
        return
    if stage == "build":
        print("Hint: check SDK path, build toolchain, and build dependencies.")
        return
    if stage == "flash":
        print("Hint: verify SWD wiring, target power, and only one debug session connected.")
        print("Hint: try a reset or power-cycle, then rerun.")
        return
    if stage == "verify":
        print("Hint: verify GPIO mapping and wiring for verify pin.")
        print("Hint: if edges are too few, lower LA sample rate or increase blink frequency.")
        return
    if stage == "observe_uart":
        print("Hint: check UART port selection and that no other process holds the port.")
        print("Hint: ensure target is running and baud rate matches firmware.")
        uart_info = uart_info if isinstance(uart_info, dict) else {}
        monitor_hint = monitor_hint if isinstance(monitor_hint, dict) else {}
        err_text = str(uart_info.get("error_summary") or "").lower()
        bytes_read = int(uart_info.get("bytes") or 0)
        permission_blocked = (
            "permission denied" in err_text
            or "permission check failed" in err_text
            or "failed to open uart port" in err_text
            or "could not open port" in err_text
            or "cannot open" in err_text
        )
        stuck_download_suspected = bool(uart_info.get("download_mode_detected")) or (bytes_read == 0 and not permission_blocked)
        if stuck_download_suspected:
            print("Hint: target appears stuck in ROM downloader ('waiting for download').")
            print("Hint: manually power-cycle or press reset, then rerun.")
            port = str(monitor_hint.get("port") or uart_info.get("port") or "/dev/ttyACM0")
            monitor_dir = str(monitor_hint.get("firmware_dir") or "").strip()
            if monitor_dir:
                print(f"Hint: if still stuck, run: cd {monitor_dir} && idf.py -p {port} monitor")
            else:
                print(f"Hint: if still stuck, run: idf.py -p {port} monitor")
        return


def _emit_event(event, notify_cfg):
    if not isinstance(notify_cfg, dict):
        return
    try:
        discord_webhook.notify(event, notify_cfg)
    except Exception as exc:
        print(f"Notify: error {exc}")


def _resolve_board_path(repo_root, board_arg):
    if not board_arg:
        return None, None
    p = Path(board_arg)
    if p.exists() and p.is_file():
        return str(p), p.stem
    board_id = board_arg
    board_path = Path(repo_root) / "configs" / "boards" / f"{board_id}.yaml"
    return str(board_path), board_id


def _normalize_until_stage(value):
    raw = str(value or "report").strip().lower()
    if raw in ("preflight", "pre-flight"):
        return "pre-flight"
    if raw in ("plan", "report"):
        return raw
    return "report"


def _filter_plan_steps_by_stage(plan_steps, until_stage):
    stage = _normalize_until_stage(until_stage)
    if stage == "plan":
        return []
    if stage == "pre-flight":
        out = []
        for step in plan_steps:
            if not isinstance(step, dict):
                continue
            if str(step.get("type", "")).startswith("preflight."):
                out.append(step)
        return out
    return list(plan_steps)


def _stage_execution_summary(until_stage):
    stages = ["plan", "pre-flight", "run", "check", "report"]
    stage = _normalize_until_stage(until_stage)
    if stage == "plan":
        executed = ["plan", "report"]
    elif stage == "pre-flight":
        executed = ["plan", "pre-flight", "report"]
    else:
        executed = list(stages)
    return {
        "requested_until": stage,
        "executed": executed,
        "deferred": [s for s in stages if s not in executed],
    }


def run_pipeline(
    probe_path,
    board_arg,
    test_path,
    wiring=None,
    output_mode="normal",
    skip_flash=False,
    no_build=False,
    verify_only=False,
    until_stage="report",
    return_paths=False,
    run_request=None,
):
    if run_request is not None:
        if isinstance(run_request, RunRequest):
            req = run_request
        else:
            req = RunRequest(
                probe_path=getattr(run_request, "probe_path", probe_path),
                board_id=getattr(run_request, "board_id", board_arg),
                test_path=getattr(run_request, "test_path", test_path),
                wiring=getattr(run_request, "wiring", wiring),
                output_mode=getattr(run_request, "output_mode", output_mode),
                skip_flash=bool(getattr(run_request, "skip_flash", skip_flash)),
                no_build=bool(getattr(run_request, "no_build", no_build)),
                verify_only=bool(getattr(run_request, "verify_only", verify_only)),
                timeout_s=getattr(run_request, "timeout_s", None),
                until_stage=getattr(run_request, "until_stage", until_stage),
            )
        probe_path = req.probe_path
        board_arg = req.board_id
        test_path = req.test_path
        wiring = req.wiring
        output_mode = req.output_mode
        skip_flash = bool(req.skip_flash)
        no_build = bool(req.no_build)
        verify_only = bool(req.verify_only)
        until_stage = getattr(req, "until_stage", until_stage)

    repo_root = str(_REPO_ROOT)
    if not test_path:
        test_path = os.path.join(repo_root, "tests", "blink_gpio.json")
    until_stage = _normalize_until_stage(until_stage)

    try:
        with open(test_path, "r", encoding="utf-8") as f:
            test_raw = json.load(f)
    except Exception:
        test_raw = {}

    board_path, board_id = _resolve_board_path(repo_root, board_arg)
    if not board_id:
        board_id = test_raw.get("board", "unknown") if isinstance(test_raw, dict) else "unknown"
        if board_id and board_id != "unknown":
            board_path, _ = _resolve_board_path(repo_root, board_id)

    run_paths = run_manager.create_run(board_id or "unknown", test_path, repo_root)
    for p in [
        run_paths.build_log,
        run_paths.flash_log,
        run_paths.observe_log,
        run_paths.observe_uart_step_log,
        run_paths.verify_log,
        run_paths.preflight_log,
    ]:
        Path(p).write_text("")
    Path(run_paths.observe_uart_log).write_bytes(b"")
    _write_json(run_paths.measure, {"ok": False, "metrics": {}, "reasons": ["not_run"]})
    _write_json(run_paths.result, {"ok": False, "failed_step": "", "error_summary": ""})
    _write_json(run_paths.flash_json, {"ok": False, "attempts": [], "strategy_used": "", "speed_khz": None})
    _write_json(run_paths.uart_observe, {"ok": False, "bytes": 0, "lines": 0})
    evidence_path = ael_evidence.write_evidence(
        Path(run_paths.root),
        "evidence.json",
        {"version": ael_evidence.EVIDENCE_VERSION, "items": []},
    )

    probe_raw = _simple_yaml_load(probe_path) if probe_path else {}
    board_raw = _simple_yaml_load(board_path) if board_path else {}
    effective = _deep_merge(_deep_merge(probe_raw, board_raw), test_raw)
    _write_json(run_paths.config_effective, effective)
    notify_cfg = effective.get("notify", {}) if isinstance(effective, dict) else {}

    run_started = datetime.now()
    run_started_mono = time.monotonic()
    git_info = _git_info()
    meta = {
        "run_id": run_paths.run_id,
        "started_at": run_started.isoformat(),
        "probe_path": probe_path,
        "board_path": board_path,
        "test_path": test_path,
        "git_commit": git_info.get("commit"),
        "git_dirty": git_info.get("dirty"),
        "git_status": git_info.get("status"),
    }
    resolved = strategy_resolver.resolve_run_strategy(
        probe_raw=probe_raw,
        board_raw=board_raw,
        test_raw=test_raw,
        wiring=wiring or "",
        request_timeout_s=(getattr(run_request, "timeout_s", None) if run_request is not None else None),
        repo_root=_REPO_ROOT,
    )
    timeout_s = resolved.timeout_s
    meta["timeout_s"] = timeout_s

    probe_cfg = resolved.probe_cfg
    board_cfg = resolved.board_cfg
    wiring_cfg = resolved.wiring_cfg
    test_name = resolved.test_name
    instrument_id = resolved.instrument_id
    instrument_host = resolved.instrument_host
    instrument_port = resolved.instrument_port
    missing_wiring = [k for k in ("swd", "reset", "verify") if wiring_cfg.get(k) == "UNKNOWN"]
    if missing_wiring:
        print(f"I am guessing {', '.join(missing_wiring)} — please confirm.")

    print("AI: starting pipeline")
    if instrument_id:
        banner_name = test_name or instrument_id
        banner_host = instrument_host or "unknown"
        banner_port = instrument_port if instrument_port is not None else "unknown"
        print(f"Using instrument: {banner_name} ({instrument_id}) @ {banner_host}:{banner_port}")
    else:
        print(f"Using probe: {probe_cfg.get('name', 'unknown')} @ {probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}")
    print(f"Using board: {board_cfg.get('name', 'unknown')} target={board_cfg.get('target', 'unknown')}")
    print(f"Wiring: swd={wiring_cfg.get('swd')} reset={wiring_cfg.get('reset')} verify={wiring_cfg.get('verify')}")

    _emit_event(
        {
            "type": "run_started",
            "severity": "info",
            "run_id": run_paths.run_id,
            "dut": board_id or board_cfg.get("name", "unknown"),
            "bench": None,
            "summary": "run started",
            "artifacts_path": str(run_paths.root),
            "timestamp": run_started.isoformat(),
            "log_paths": {
                "build": str(run_paths.build_log),
                "flash": str(run_paths.flash_log),
                "observe": str(run_paths.observe_log),
                "verify": str(run_paths.verify_log),
                "uart": str(run_paths.observe_uart_log),
            },
        },
        notify_cfg,
    )

    def _failed_step_name(runner_result):
        if runner_result.get("ok"):
            return ""
        steps = runner_result.get("steps", []) if isinstance(runner_result, dict) else []
        for entry in reversed(steps):
            if isinstance(entry, dict) and not entry.get("ok", False):
                return str(entry.get("name", ""))
        return ""

    def _code_from_failed_step(name):
        if not name:
            return 1
        if name.startswith("preflight"):
            return 2
        if name.startswith("instrument_selftest"):
            return 7
        if name.startswith("build"):
            return 3
        if name.startswith("load"):
            return 4
        if name.startswith("check_uart"):
            return 5
        if name.startswith("check"):
            return 6
        return 1

    def _extract_firmware_from_runner(runner_result):
        steps = runner_result.get("steps", []) if isinstance(runner_result, dict) else []
        for entry in reversed(steps):
            if not isinstance(entry, dict):
                continue
            payload = entry.get("result", {})
            if isinstance(payload, dict) and payload.get("firmware_path"):
                return str(payload.get("firmware_path"))
        return None

    plan_steps = []
    preflight_step = strategy_resolver.build_preflight_step(
        test_raw=test_raw,
        probe_cfg=probe_cfg,
        out_json=str(run_paths.preflight),
        output_mode=output_mode,
        log_path=str(run_paths.preflight_log),
    )
    if preflight_step is not None:
        plan_steps.append(preflight_step)
    else:
        _write_json(run_paths.preflight, {"skipped": True})
        with _tee_output(run_paths.preflight_log, output_mode):
            print("Preflight: SKIPPED (test config)")

    instrument_selftest_step = strategy_resolver.build_instrument_selftest_step(
        test_raw=test_raw,
        board_cfg=board_cfg,
        artifacts_dir=Path(run_paths.artifacts_dir),
    )
    if instrument_selftest_step is not None:
        plan_steps.append(instrument_selftest_step)

    build_kind, known_firmware_path, build_step = strategy_resolver.resolve_build_stage(
        board_cfg=board_cfg,
        verify_only=verify_only,
        no_build=no_build,
        repo_root=_REPO_ROOT,
        output_mode=output_mode,
        build_log_path=str(run_paths.build_log),
    )
    if build_step is not None:
        plan_steps.append(build_step)
    elif not verify_only and no_build:
        if not os.path.exists(known_firmware_path):
            result = {
                "run_id": run_paths.run_id,
                "termination": RunTermination.FAIL,
                "ok": False,
                "success": False,
                "failed_step": "build",
                "error_summary": "no build artifacts found",
                "started_at": run_started.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "timeout_s": timeout_s,
                "retry_summary": {"step_attempts": 0, "recovery_attempts": 0},
                "logs": {
                    "preflight": str(run_paths.preflight_log),
                    "build": str(run_paths.build_log),
                    "flash": str(run_paths.flash_log),
                    "observe": str(run_paths.observe_log),
                    "observe_uart": str(run_paths.observe_uart_step_log),
                    "observe_uart_raw": str(run_paths.observe_uart_log),
                    "verify": str(run_paths.verify_log),
                },
                "artifacts": [],
                "json": {
                    "flash": str(run_paths.flash_json),
                    "measure": str(run_paths.measure),
                    "uart_observe": str(run_paths.uart_observe),
                    "preflight": str(run_paths.preflight),
                    "meta": str(run_paths.meta),
                    "config_effective": str(run_paths.config_effective),
                    "instrument_selftest": str(Path(run_paths.artifacts_dir) / "instrument_selftest.json"),
                    "instrument_digital": str(Path(run_paths.artifacts_dir) / "instrument_digital.json"),
                    "verify_result": str(Path(run_paths.artifacts_dir) / "verify_result.json"),
                    "evidence": str(evidence_path),
                },
                "evidence": {"version": ael_evidence.EVIDENCE_VERSION, "count": 0, "status_counts": {"pass": 0, "fail": 0, "info": 0}},
            }
            _write_json(run_paths.result, result)
            meta["ended_at"] = result["ended_at"]
            meta["termination"] = RunTermination.FAIL
            _write_json(run_paths.meta, meta)
            return (3, run_paths) if return_paths else 3

    load_step, flash_cfg = strategy_resolver.resolve_load_stage(
        board_cfg=board_cfg,
        wiring_cfg=wiring_cfg,
        probe_cfg=probe_cfg,
        known_firmware_path=known_firmware_path,
        verify_only=verify_only,
        skip_flash=skip_flash,
        repo_root=_REPO_ROOT,
        output_mode=output_mode,
        flash_json_path=str(run_paths.flash_json),
        flash_log_path=str(run_paths.flash_log),
    )
    if load_step is not None:
        plan_steps.append(load_step)
    elif skip_flash and not verify_only:
        with _tee_output(run_paths.flash_log, output_mode):
            print("Flash: SKIPPED (user requested skip)")
        _write_json(
            run_paths.flash_json,
            {"ok": False, "attempts": [], "strategy_used": "skipped", "speed_khz": flash_cfg.get("speed_khz")},
        )

    uart_step = strategy_resolver.build_uart_step(
        effective=effective,
        board_cfg=board_cfg,
        output_mode=output_mode,
        observe_uart_log=str(run_paths.observe_uart_log),
        uart_json=str(run_paths.uart_observe),
        flash_json=str(run_paths.flash_json),
        observe_uart_step_log=str(run_paths.observe_uart_step_log),
    )
    if uart_step is not None:
        plan_steps.append(uart_step)

    verify_step = strategy_resolver.build_verify_step(
        test_raw=test_raw,
        board_cfg=board_cfg,
        probe_cfg=probe_cfg,
        wiring_cfg=wiring_cfg,
        artifacts_dir=Path(run_paths.artifacts_dir),
        observe_log=str(run_paths.observe_log),
        output_mode=output_mode,
        measure_path=str(run_paths.measure),
    )
    plan_steps.append(verify_step)

    plan = {
        "version": "runplan/0.1",
        "plan_id": run_paths.run_id,
        "created_at": run_started.isoformat(),
        "inputs": {
            "board_id": board_id or "unknown",
            "probe_id": probe_cfg.get("name"),
            "instrument_id": (strategy_resolver.resolve_instrument_context(test_raw, board_cfg)[0] if isinstance(test_raw, dict) else None),
            "test_id": Path(test_path).stem,
        },
        "selected": {
            "board_config": str(board_path) if board_path else "",
            "probe_config": str(probe_path) if probe_path else "",
            "test_config": str(test_path),
        },
        "context": {
            "workspace_dir": str(repo_root),
            "run_root": str(Path(run_paths.root).parent),
            "artifact_root": str(Path(run_paths.root) / "artifacts"),
            "log_root": str(Path(run_paths.root)),
        },
        "preflight": {"checks": [{"type": "probe.health", "args": {}}], "policy": {"fail_fast": True}},
        "steps": plan_steps,
        "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"build": 1, "run": 2, "check": 2}},
        "report": {"emit": ["*.log", "*.json", "artifacts/*"]},
    }
    if timeout_s is not None:
        plan["timeout_s"] = timeout_s
    plan["stage_execution"] = _stage_execution_summary(until_stage)
    plan["stages"] = ["plan", "pre-flight", "run", "check", "report"]

    registry = AdapterRegistry()
    runner_plan = dict(plan)
    runner_plan["steps"] = _filter_plan_steps_by_stage(plan_steps, until_stage)
    runner_result = run_plan(runner_plan, Path(run_paths.root), registry)
    evidence_path = ael_evidence.write_runner_evidence(Path(run_paths.root), runner_result)
    evidence_payload = {}
    try:
        evidence_payload = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    except Exception:
        evidence_payload = {"version": ael_evidence.EVIDENCE_VERSION, "items": []}
    evidence_items = evidence_payload.get("items", []) if isinstance(evidence_payload, dict) else []
    evidence_counts = {"pass": 0, "fail": 0, "info": 0}
    for item in evidence_items if isinstance(evidence_items, list) else []:
        if not isinstance(item, dict):
            continue
        st = str(item.get("status") or "").strip().lower()
        if st in evidence_counts:
            evidence_counts[st] += 1

    failed_step = _failed_step_name(runner_result)
    firmware_path = known_firmware_path or _extract_firmware_from_runner(runner_result)
    artifacts_copied = _copy_artifacts(firmware_path, run_paths.artifacts_dir)

    meter_verify = strategy_resolver.is_meter_digital_verify_test(test_raw, board_cfg)
    if meter_verify:
        _write_json(run_paths.measure, {"ok": bool(runner_result.get("ok")), "type": "instrument_digital_verify"})

    ended_at = datetime.now().isoformat()
    termination = str(runner_result.get("termination") or (RunTermination.PASS if runner_result.get("ok") else RunTermination.FAIL))
    if termination not in RunTermination.ALL:
        termination = RunTermination.FAIL
    result = {
        "run_id": run_paths.run_id,
        "termination": termination,
        "ok": bool(runner_result.get("ok", False)),
        "success": bool(runner_result.get("ok", False)),
        "failed_step": failed_step,
        "error_summary": runner_result.get("error_summary", ""),
        "started_at": run_started.isoformat(),
        "ended_at": ended_at,
        "timeout_s": timeout_s,
        "retry_summary": {
            "step_attempts": len(runner_result.get("steps", [])) if isinstance(runner_result.get("steps"), list) else 0,
            "recovery_attempts": len(runner_result.get("recovery", [])) if isinstance(runner_result.get("recovery"), list) else 0,
        },
        "logs": {
            "preflight": str(run_paths.preflight_log),
            "build": str(run_paths.build_log),
            "flash": str(run_paths.flash_log),
            "observe": str(run_paths.observe_log),
            "observe_uart": str(run_paths.observe_uart_step_log),
            "observe_uart_raw": str(run_paths.observe_uart_log),
            "verify": str(run_paths.verify_log),
        },
        "artifacts": artifacts_copied,
        "json": {
            "flash": str(run_paths.flash_json),
            "measure": str(run_paths.measure),
            "uart_observe": str(run_paths.uart_observe),
            "preflight": str(run_paths.preflight),
            "meta": str(run_paths.meta),
            "config_effective": str(run_paths.config_effective),
            "instrument_selftest": str(Path(run_paths.artifacts_dir) / "instrument_selftest.json"),
            "instrument_digital": str(Path(run_paths.artifacts_dir) / "instrument_digital.json"),
            "verify_result": str(Path(run_paths.artifacts_dir) / "verify_result.json"),
            "run_plan": str(Path(run_paths.artifacts_dir) / "run_plan.json"),
            "runner_result": str(Path(run_paths.artifacts_dir) / "result.json"),
            "evidence": str(evidence_path),
        },
        "evidence": {
            "version": evidence_payload.get("version") if isinstance(evidence_payload, dict) else ael_evidence.EVIDENCE_VERSION,
            "count": len(evidence_items) if isinstance(evidence_items, list) else 0,
            "status_counts": evidence_counts,
        },
        "stage_execution": _stage_execution_summary(until_stage),
    }
    _write_json(run_paths.result, result)

    timings = {"total_s": round(time.monotonic() - run_started_mono, 3)}
    for s in ("preflight", "build", "load", "check_uart", "check_meter", "check_signal", "instrument_selftest"):
        entries = [x for x in runner_result.get("steps", []) if isinstance(x, dict) and x.get("name") == s]
        if entries:
            timings[f"{s}_attempts"] = len(entries)
    meta.update(
        {
            "ended_at": ended_at,
            "timings": timings,
            "termination": termination,
            "firmware": {"path": firmware_path, "sha256": _file_sha256(firmware_path) if firmware_path else ""},
            "runner_result": str(Path(run_paths.artifacts_dir) / "result.json"),
            "run_plan": str(Path(run_paths.artifacts_dir) / "run_plan.json"),
        }
    )
    _write_json(run_paths.meta, meta)

    if result["ok"]:
        print("PASS: Run verified")
        _emit_event(
            {
                "type": "run_succeeded",
                "severity": "info",
                "run_id": run_paths.run_id,
                "dut": board_id or board_cfg.get("name", "unknown"),
                "bench": None,
                "step": "verify",
                "summary": "run succeeded",
                "details": "",
                "artifacts_path": str(run_paths.root),
                "timestamp": datetime.now().isoformat(),
                "log_paths": {
                    "build": str(run_paths.build_log),
                    "flash": str(run_paths.flash_log),
                    "observe": str(run_paths.observe_log),
                    "verify": str(run_paths.verify_log),
                    "uart": str(run_paths.observe_uart_log),
                },
            },
            notify_cfg,
        )
        return (0, run_paths) if return_paths else 0

    err_l = str(result["error_summary"]).lower()
    if "permission check failed" in err_l or "permission denied" in err_l:
        print("UART: permission check failed.")
        print("Action required: fix /dev/tty* permission/group manually, then rerun.")
    if "download mode" in err_l:
        print("UART: target entered bootloader download mode.")
        print("Action: reset DUT and rerun. Auto RTS reset was already attempted.")

    fail_stage = "verify"
    if failed_step.startswith("preflight"):
        fail_stage = "preflight"
    elif failed_step.startswith("build"):
        fail_stage = "build"
    elif failed_step.startswith("load"):
        fail_stage = "flash"
    elif failed_step.startswith("check_uart"):
        fail_stage = "observe_uart"
    uart_info = {}
    monitor_hint = {}
    if fail_stage == "observe_uart":
        try:
            uart_info = json.loads(Path(run_paths.uart_observe).read_text(encoding="utf-8"))
        except Exception:
            uart_info = {}
        fw_dir = ""
        if isinstance(test_raw, dict):
            fw_dir = str(test_raw.get("firmware") or "").strip()
        if not fw_dir and isinstance(board_cfg, dict):
            fw_dir = str((board_cfg.get("build") or {}).get("project_dir") or "").strip()
        if fw_dir and not os.path.isabs(fw_dir):
            fw_dir = str((_REPO_ROOT / fw_dir).resolve())
        monitor_hint = {"firmware_dir": fw_dir, "port": str(uart_info.get("port") or "/dev/ttyACM0")}

    _triage(fail_stage, {}, uart_info=uart_info, monitor_hint=monitor_hint)

    _emit_event(
        {
            "type": "run_failed",
            "severity": "error",
            "run_id": run_paths.run_id,
            "dut": board_id or board_cfg.get("name", "unknown"),
            "bench": None,
            "step": failed_step or "runner",
            "summary": result.get("error_summary", "run failed"),
            "details": "",
            "artifacts_path": str(run_paths.root),
            "timestamp": datetime.now().isoformat(),
            "log_paths": {
                "preflight": str(run_paths.preflight_log),
                "build": str(run_paths.build_log),
                "flash": str(run_paths.flash_log),
                "observe": str(run_paths.observe_log),
                "verify": str(run_paths.verify_log),
                "uart": str(run_paths.observe_uart_log),
            },
        },
        notify_cfg,
    )
    if termination == RunTermination.TIMEOUT:
        code = 124
    elif termination == RunTermination.SAFETY_ABORT:
        code = 70
    else:
        code = _code_from_failed_step(failed_step)
    return (code, run_paths) if return_paths else code


def run(args):
    return run_pipeline(
        probe_path=None,
        board_arg=None,
        test_path=None,
        run_request=RunRequest(
            probe_path=args.probe,
            board_id=args.board,
            test_path=args.test,
            wiring=args.wiring,
            output_mode=args.output_mode,
            skip_flash=bool(args.skip_flash),
            until_stage=getattr(args, "until_stage", "report"),
        ),
    )


def run_cli(probe_path, board_id, test_path, wiring=None, output_mode="normal", until_stage="report"):
    return run_pipeline(
        probe_path=None,
        board_arg=None,
        test_path=None,
        run_request=RunRequest(
            probe_path=probe_path,
            board_id=board_id,
            test_path=test_path,
            wiring=wiring,
            output_mode=output_mode,
            until_stage=until_stage,
        ),
    )


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--probe", required=True)
    run_p.add_argument("--board", required=True)
    run_p.add_argument("--test", required=False, default=os.path.join("tests", "blink_gpio.json"))
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--skip-flash", action="store_true")
    run_p.add_argument(
        "--until-stage",
        required=False,
        default="report",
        help="Stop after stage: plan, pre-flight, or report (default full flow).",
    )
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    args = parser.parse_args()
    if args.cmd == "run":
        if args.verbose:
            args.output_mode = "verbose"
        elif args.quiet:
            args.output_mode = "quiet"
        else:
            args.output_mode = "normal"
        code = run(args)
        sys.exit(code)


if __name__ == "__main__":
    main()
