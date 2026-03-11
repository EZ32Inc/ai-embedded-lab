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
from ael import workflow_archive
from ael.instruments import provision as instrument_provision
from ael.adapter_registry import AdapterRegistry
from ael.runner import run_plan
from ael.run_contract import RunRequest, RunTermination
from ael import strategy_resolver
from ael.config_resolver import resolve_probe_instance
from ael.connection_model import build_connection_digest, build_connection_setup, wiring_assumption_lines
from ael.probe_binding import empty_probe_binding, load_probe_binding

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


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _verify_failure_observations(runner_result):
    if not isinstance(runner_result, dict):
        return {}
    steps = runner_result.get("steps", [])
    if not isinstance(steps, list):
        return {}
    failed = None
    for entry in reversed(steps):
        if isinstance(entry, dict) and not bool(entry.get("ok", False)):
            failed = entry
            break
    if not isinstance(failed, dict):
        return {}
    out = failed.get("result", {})
    if not isinstance(out, dict):
        return {}
    evidence = out.get("evidence")
    items = evidence if isinstance(evidence, list) else ([evidence] if isinstance(evidence, dict) else [])
    primary = items[0] if items and isinstance(items[0], dict) else {}
    facts = primary.get("facts") if isinstance(primary.get("facts"), dict) else {}
    verify_substage = str(
        out.get("verify_substage")
        or facts.get("verify_substage")
        or primary.get("kind")
        or ""
    ).strip()
    failure_class = str(
        out.get("failure_class")
        or facts.get("failure_class")
        or out.get("failure_kind")
        or facts.get("failure_kind")
        or ""
    ).strip()
    return {
        "verify_substage": verify_substage,
        "failure_class": failure_class,
        "observations": dict(facts) if isinstance(facts, dict) else {},
    }


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
    run_manager.ensure_thread_output_proxies()
    tee, f = run_manager.open_tee(Path(log_path), output_mode, console=run_manager.base_stdout())
    try:
        with run_manager.route_thread_output(tee):
            yield
    finally:
        try:
            tee.flush()
        except Exception:
            pass
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
    if raw in ("plan", "run", "run-exit", "check", "report"):
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
    if stage in ("run", "run-exit"):
        out = []
        for step in plan_steps:
            if not isinstance(step, dict):
                continue
            step_type = str(step.get("type", ""))
            if step_type.startswith("check."):
                continue
            out.append(step)
        return out
    return list(plan_steps)


def _stage_execution_summary(until_stage, *, preflight_enabled=True):
    stages = ["plan", "pre-flight", "run", "check", "report"]
    stage = _normalize_until_stage(until_stage)
    executed = ["plan"]
    skipped = []
    if stage == "plan":
        if not preflight_enabled:
            skipped.append("pre-flight")
    elif stage == "pre-flight":
        if preflight_enabled:
            executed.append("pre-flight")
        else:
            skipped.append("pre-flight")
    elif stage in ("run", "run-exit"):
        if preflight_enabled:
            executed.append("pre-flight")
        else:
            skipped.append("pre-flight")
        executed.append("run")
    else:
        if preflight_enabled:
            executed.append("pre-flight")
        else:
            skipped.append("pre-flight")
        executed.extend(["run", "check"])
    executed.append("report")
    return {
        "requested_until": stage,
        "executed": executed,
        "skipped": skipped,
        "deferred": [s for s in stages if s not in executed and s not in skipped],
    }


def _key_passed_checks(evidence_payload):
    checks = []
    items = evidence_payload.get("items", []) if isinstance(evidence_payload, dict) else []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or str(item.get("status") or "").lower() != "pass":
            continue
        checks.append(str(item.get("kind") or item.get("summary") or item.get("source") or "pass"))
    return checks


def _build_validation_summary(
    *,
    run_id,
    board_cfg,
    test_path,
    run_result_path,
    result,
    flash_info,
    evidence_payload,
    instrument_id,
    instrument_host,
    instrument_port,
    instrument_communication,
    instrument_capability_surfaces,
    probe_instance_id,
    probe_type,
    probe_host,
    probe_port,
    probe_communication,
    probe_capability_surfaces,
    selected_ssid,
    connection_setup,
):
    summary = {
        "board": board_cfg.get("name"),
        "test": Path(test_path).stem,
        "run_id": run_id,
        "overall_result": "pass" if result.get("ok") else "fail",
        "executed_stages": list((result.get("stage_execution") or {}).get("executed", [])),
        "key_checks_passed": _key_passed_checks(evidence_payload),
        "serial_or_flash_port": flash_info.get("port") or None,
        "instrument_profile": instrument_id or None,
        "endpoint": f"{instrument_host}:{instrument_port}" if instrument_host and instrument_port is not None else None,
        "instrument_communication": dict(instrument_communication or {}),
        "instrument_capability_surfaces": dict(instrument_capability_surfaces or {}),
        "probe_instance": probe_instance_id or None,
        "probe_type": probe_type or None,
        "probe_endpoint": f"{probe_host}:{probe_port}" if probe_host and probe_port is not None else None,
        "probe_communication": dict(probe_communication or {}),
        "probe_capability_surfaces": dict(probe_capability_surfaces or {}),
        "key_artifact_paths": {
            "run_plan": (result.get("json") or {}).get("run_plan"),
            "runner_result": (result.get("json") or {}).get("runner_result"),
            "result": run_result_path,
        },
        "key_evidence_paths": {
            "evidence": (result.get("json") or {}).get("evidence"),
            "verify_result": (result.get("json") or {}).get("verify_result"),
            "uart_observe": (result.get("json") or {}).get("uart_observe"),
        },
        "cleanup_items": [],
        "connection_setup": dict(connection_setup or {}),
        "connection_digest": build_connection_digest(connection_setup),
    }
    if selected_ssid:
        summary["selected_ap_ssid"] = selected_ssid
    skipped = list((result.get("stage_execution") or {}).get("skipped", []))
    if "pre-flight" in skipped:
        summary["cleanup_items"].append("pre-flight skipped by configuration")
    return summary


def _build_current_setup(
    *,
    flash_info,
    instrument_id,
    instrument_host,
    instrument_port,
    instrument_communication,
    instrument_capability_surfaces,
    probe_instance_id,
    probe_type,
    probe_host,
    probe_port,
    probe_communication,
    probe_capability_surfaces,
    selected_ssid,
    connection_setup,
):
    setup = {
        "serial_or_flash_port": flash_info.get("port") or None,
        "instrument_profile": instrument_id or None,
        "instrument_communication": dict(instrument_communication or {}),
        "instrument_capability_surfaces": dict(instrument_capability_surfaces or {}),
        "probe_instance": probe_instance_id or None,
        "probe_type": probe_type or None,
        "probe_endpoint": {
            "host": probe_host or None,
            "port": probe_port if probe_port is not None else None,
        },
        "probe_communication": dict(probe_communication or {}),
        "probe_capability_surfaces": dict(probe_capability_surfaces or {}),
        "selected_endpoint": {
            "host": instrument_host or None,
            "port": instrument_port if instrument_port is not None else None,
        },
        "connection_setup": dict(connection_setup or {}),
        "connection_digest": build_connection_digest(connection_setup),
    }
    if selected_ssid:
        setup["selected_ap_ssid"] = selected_ssid
    return setup


def _build_last_known_good_setup(
    *,
    run_id,
    board_cfg,
    test_path,
    flash_info,
    instrument_id,
    instrument_host,
    instrument_port,
    instrument_communication,
    instrument_capability_surfaces,
    probe_instance_id,
    probe_type,
    probe_host,
    probe_port,
    probe_communication,
    probe_capability_surfaces,
    selected_ssid,
    connection_setup,
    result,
):
    setup = {
        "board": board_cfg.get("name"),
        "test": Path(test_path).stem,
        "port": flash_info.get("port") or None,
        "instrument_profile": instrument_id or None,
        "endpoint": f"{instrument_host}:{instrument_port}" if instrument_host and instrument_port is not None else None,
        "instrument_communication": dict(instrument_communication or {}),
        "instrument_capability_surfaces": dict(instrument_capability_surfaces or {}),
        "probe_instance": probe_instance_id or None,
        "probe_type": probe_type or None,
        "probe_endpoint": f"{probe_host}:{probe_port}" if probe_host and probe_port is not None else None,
        "probe_communication": dict(probe_communication or {}),
        "probe_capability_surfaces": dict(probe_capability_surfaces or {}),
        "run_id": run_id,
        "artifact_or_evidence_location": (result.get("json") or {}).get("evidence"),
        "connection_setup": dict(connection_setup or {}),
        "connection_digest": build_connection_digest(connection_setup),
    }
    wiring = (connection_setup or {}).get("wiring_assumptions") if isinstance(connection_setup, dict) else None
    if wiring:
        setup["wiring_assumptions"] = wiring
    if selected_ssid:
        setup["selected_ap_ssid"] = selected_ssid
    return setup


def _format_capability_surfaces(mapping: dict | None) -> str | None:
    if not isinstance(mapping, dict) or not mapping:
        return None
    parts = []
    for key in sorted(mapping):
        value = mapping.get(key)
        cap = str(key).strip()
        surface = str(value).strip() if value is not None else ""
        if cap and surface:
            parts.append(f"{cap}->{surface}")
    return ", ".join(parts) if parts else None


def _print_success_summary(summary, last_known_good, current_setup):
    print(
        "Summary: validation "
        f"board={summary.get('board')} test={summary.get('test')} run_id={summary.get('run_id')} "
        f"result={summary.get('overall_result')}"
    )
    print(f"Summary: executed_stages={','.join(summary.get('executed_stages', []))}")
    if summary.get("key_checks_passed"):
        print(f"Summary: key_checks_passed={', '.join(summary.get('key_checks_passed', []))}")
    if summary.get("serial_or_flash_port"):
        print(f"Summary: port={summary.get('serial_or_flash_port')}")
    if summary.get("instrument_profile"):
        line = f"Summary: instrument={summary.get('instrument_profile')}"
        if summary.get("selected_ap_ssid"):
            line += f" ssid={summary.get('selected_ap_ssid')}"
        if summary.get("endpoint"):
            line += f" endpoint={summary.get('endpoint')}"
        print(line)
        surfaces = _format_capability_surfaces(summary.get("instrument_capability_surfaces"))
        if surfaces:
            print(f"Summary: instrument_surfaces={surfaces}")
    if summary.get("probe_instance"):
        line = f"Summary: probe_instance={summary.get('probe_instance')}"
        if summary.get("probe_type"):
            line += f" type={summary.get('probe_type')}"
        if summary.get("probe_endpoint"):
            line += f" endpoint={summary.get('probe_endpoint')}"
        print(line)
        surfaces = _format_capability_surfaces(summary.get("probe_capability_surfaces"))
        if surfaces:
            print(f"Summary: probe_surfaces={surfaces}")
    print(
        "Summary: artifacts "
        f"result={summary.get('key_artifact_paths', {}).get('result')} "
        f"run_plan={summary.get('key_artifact_paths', {}).get('run_plan')}"
    )
    print(
        "Summary: evidence "
        f"evidence={summary.get('key_evidence_paths', {}).get('evidence')} "
        f"verify={summary.get('key_evidence_paths', {}).get('verify_result')}"
    )
    if summary.get("cleanup_items"):
        print(f"Summary: caveats={', '.join(summary.get('cleanup_items', []))}")
    endpoint = current_setup.get("selected_endpoint", {}) if isinstance(current_setup.get("selected_endpoint"), dict) else {}
    probe_endpoint = current_setup.get("probe_endpoint", {}) if isinstance(current_setup.get("probe_endpoint"), dict) else {}
    setup_line = "Summary: setup"
    if current_setup.get("serial_or_flash_port"):
        setup_line += f" port={current_setup.get('serial_or_flash_port')}"
    if current_setup.get("selected_ap_ssid"):
        setup_line += f" ssid={current_setup.get('selected_ap_ssid')}"
    if endpoint.get("host") and endpoint.get("port") is not None:
        setup_line += f" endpoint={endpoint.get('host')}:{endpoint.get('port')}"
    if current_setup.get("instrument_profile"):
        setup_line += f" instrument={current_setup.get('instrument_profile')}"
    if current_setup.get("probe_instance"):
        setup_line += f" probe_instance={current_setup.get('probe_instance')}"
    if probe_endpoint.get("host") and probe_endpoint.get("port") is not None:
        setup_line += f" probe_endpoint={probe_endpoint.get('host')}:{probe_endpoint.get('port')}"
    print(setup_line)
    conn = current_setup.get("connection_setup", {}) if isinstance(current_setup.get("connection_setup"), dict) else {}
    if conn.get("warnings"):
        print(f"Summary: connection_warnings={'; '.join(conn.get('warnings', []))}")
    if current_setup.get("connection_digest"):
        print(f"Summary: connection_digest={'; '.join(current_setup.get('connection_digest', []))}")
    print(
        "LKG: "
        f"board={last_known_good.get('board')} test={last_known_good.get('test')} "
        f"port={last_known_good.get('port')} run_id={last_known_good.get('run_id')}"
    )
    if last_known_good.get("instrument_profile"):
        line = f"LKG: instrument={last_known_good.get('instrument_profile')}"
        if last_known_good.get("selected_ap_ssid"):
            line += f" ssid={last_known_good.get('selected_ap_ssid')}"
        if last_known_good.get("endpoint"):
            line += f" endpoint={last_known_good.get('endpoint')}"
        print(line)
        surfaces = _format_capability_surfaces(last_known_good.get("instrument_capability_surfaces"))
        if surfaces:
            print(f"LKG: instrument_surfaces={surfaces}")
    if last_known_good.get("probe_instance"):
        line = f"LKG: probe_instance={last_known_good.get('probe_instance')}"
        if last_known_good.get("probe_type"):
            line += f" type={last_known_good.get('probe_type')}"
        if last_known_good.get("probe_endpoint"):
            line += f" endpoint={last_known_good.get('probe_endpoint')}"
        print(line)
        surfaces = _format_capability_surfaces(last_known_good.get("probe_capability_surfaces"))
        if surfaces:
            print(f"LKG: probe_surfaces={surfaces}")
    if last_known_good.get("wiring_assumptions"):
        print(f"LKG: wiring={'; '.join(last_known_good.get('wiring_assumptions', []))}")
    conn = last_known_good.get("connection_setup", {}) if isinstance(last_known_good.get("connection_setup"), dict) else {}
    if conn.get("warnings"):
        print(f"LKG: connection_warnings={'; '.join(conn.get('warnings', []))}")
    if last_known_good.get("connection_digest"):
        print(f"LKG: connection_digest={'; '.join(last_known_good.get('connection_digest', []))}")
    print(f"LKG: evidence={last_known_good.get('artifact_or_evidence_location')}")


def _should_check_meter_reachability(until_stage, test_raw, board_cfg):
    stage = _normalize_until_stage(until_stage)
    if stage in ("plan", "pre-flight"):
        return False
    if not strategy_resolver.is_meter_digital_verify_test(test_raw, board_cfg):
        return False
    instrument_id, _tcp_cfg, _manifest = strategy_resolver.resolve_instrument_context(test_raw, board_cfg)
    return str(instrument_id or "").strip() == "esp32s3_dev_c_meter"


def _ensure_meter_reachable_for_run(test_raw, board_cfg):
    instrument_id, tcp_cfg, manifest = strategy_resolver.resolve_instrument_context(test_raw, board_cfg)
    manifest_payload = dict(manifest) if isinstance(manifest, dict) else {}
    manifest_payload.setdefault("id", instrument_id)
    wifi_cfg = manifest_payload.get("wifi") if isinstance(manifest_payload.get("wifi"), dict) else {}
    if not wifi_cfg:
        wifi_cfg = {}
    if tcp_cfg.get("host") and "ap_ip" not in wifi_cfg:
        wifi_cfg["ap_ip"] = tcp_cfg.get("host")
    manifest_payload["wifi"] = wifi_cfg
    return instrument_provision.ensure_meter_reachable(
        manifest=manifest_payload,
        host=tcp_cfg.get("host"),
    )


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

    board_raw = _simple_yaml_load(board_path) if board_path else {}
    board_probe_instance = resolve_probe_instance(repo_root, args=None, board_id=board_id)
    if probe_path or board_probe_instance:
        binding = load_probe_binding(
            repo_root,
            probe_path=probe_path,
            instance_id=board_probe_instance if not probe_path else None,
        )
    else:
        binding = empty_probe_binding()
    probe_path = binding.config_path
    probe_raw = binding.raw
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
    instrument_communication = resolved.instrument_communication
    instrument_capability_surfaces = resolved.instrument_capability_surfaces
    conn_setup = build_connection_setup(resolved.connection_ctx)
    conn_setup["wiring_assumptions"] = wiring_assumption_lines(resolved.connection_ctx)
    probe_instance_id = binding.instance_id
    probe_type = binding.type_id
    probe_host = binding.endpoint_host or probe_cfg.get("ip")
    probe_port = binding.endpoint_port or probe_cfg.get("gdb_port")
    probe_communication = binding.communication
    probe_capability_surfaces = binding.capability_surfaces
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
        if probe_instance_id:
            print(f"Using probe instance: {probe_instance_id} ({probe_type or probe_cfg.get('name', 'unknown')}) @ {probe_host or 'unknown'}:{probe_port or 'unknown'}")
        else:
            print(f"Using probe: {probe_cfg.get('name', 'unknown')} @ {probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}")
    if binding.legacy_warning:
        print(f"Warning: {binding.legacy_warning}")
    print(f"Using board: {board_cfg.get('name', 'unknown')} target={board_cfg.get('target', 'unknown')}")
    print(f"Wiring: swd={wiring_cfg.get('swd')} reset={wiring_cfg.get('reset')} verify={wiring_cfg.get('verify')}")

    archive_context = workflow_archive.env_conversation_context()
    archive_base = {
        "run_id": run_paths.run_id,
        "session_id": archive_context.get("session_id"),
        "task_id": archive_context.get("task_id"),
        "board": {
            "id": board_id or "unknown",
            "name": board_cfg.get("name"),
            "target": board_cfg.get("target"),
        },
        "test": {
            "name": Path(test_path).stem,
            "path": str(test_path),
        },
        "probe": {
            "name": probe_cfg.get("name"),
            "path": probe_path,
            "instance_id": probe_instance_id,
            "type": probe_type,
            "endpoint": {"host": probe_host, "port": probe_port},
            "communication": dict(probe_communication or {}),
            "capability_surfaces": dict(probe_capability_surfaces or {}),
            "legacy_warning": binding.legacy_warning,
        },
        "instrument": {
            "id": instrument_id,
            "host": instrument_host,
            "port": instrument_port,
            "communication": dict(instrument_communication or {}),
            "capability_surfaces": dict(instrument_capability_surfaces or {}),
        },
        "selected": {
            "board_config": str(board_path) if board_path else None,
            "probe_config": str(probe_path) if probe_path else None,
            "test_config": str(test_path),
        },
        "connection": dict(conn_setup),
        "connection_digest": build_connection_digest(conn_setup),
    }

    workflow_archive.append_event(
        {
            **archive_base,
            **workflow_archive.runtime_event(
                action="run_started",
                status="started",
                stage="plan",
                extra={
                    "requested_until_stage": until_stage,
                    "artifacts": {
                        "run_root": str(run_paths.root),
                        "config_effective": str(run_paths.config_effective),
                        "meta": str(run_paths.meta),
                    },
                },
            ),
        },
        run_root=run_paths.root,
    )
    if archive_context.get("user_request"):
        workflow_archive.append_event(
            {
                **archive_base,
                **workflow_archive.workflow_event(
                    actor="user",
                    action="request",
                    text=archive_context.get("user_request"),
                    status="captured",
                    stage="plan",
                ),
            },
            run_root=run_paths.root,
        )
    if archive_context.get("ai_response"):
        workflow_archive.append_event(
            {
                **archive_base,
                **workflow_archive.workflow_event(
                    actor="assistant",
                    action="response",
                    text=archive_context.get("ai_response"),
                    status="captured",
                    stage="plan",
                ),
            },
            run_root=run_paths.root,
        )
    if archive_context.get("user_confirmation"):
        workflow_archive.append_event(
            {
                **archive_base,
                **workflow_archive.workflow_event(
                    actor="user",
                    action="confirmation",
                    text=archive_context.get("user_confirmation"),
                    status="captured",
                    stage="plan",
                ),
            },
            run_root=run_paths.root,
        )
    if archive_context.get("user_correction"):
        workflow_archive.append_event(
            {
                **archive_base,
                **workflow_archive.workflow_event(
                    actor="user",
                    action="correction",
                    text=archive_context.get("user_correction"),
                    status="captured",
                    stage="plan",
                ),
            },
            run_root=run_paths.root,
        )
    if archive_context.get("ai_next_action"):
        workflow_archive.append_event(
            {
                **archive_base,
                **workflow_archive.workflow_event(
                    actor="assistant",
                    action="next_action",
                    text=archive_context.get("ai_next_action"),
                    status="planned",
                    stage=until_stage,
                ),
            },
            run_root=run_paths.root,
        )

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

    if _should_check_meter_reachability(until_stage, test_raw, board_cfg):
        try:
            _ensure_meter_reachable_for_run(test_raw, board_cfg)
        except Exception as exc:
            error_summary = str(exc)
            print(error_summary)
            details = getattr(exc, "details", {}) if isinstance(getattr(exc, "details", {}), dict) else {}
            early_evidence_item = ael_evidence.make_item(
                kind="instrument.reachability",
                source="check.meter_reachability",
                ok=False,
                summary=error_summary,
                facts=details,
                artifacts={},
            )
            evidence_path = ael_evidence.write_evidence(
                Path(run_paths.root),
                "evidence.json",
                {"version": ael_evidence.EVIDENCE_VERSION, "items": [early_evidence_item]},
            )
            ended_at = datetime.now().isoformat()
            result = {
                "run_id": run_paths.run_id,
                "termination": RunTermination.FAIL,
                "ok": False,
                "success": False,
                "failed_step": "check_meter_reachability",
                "error_summary": error_summary,
                "failure_class": details.get("failure_class"),
                "observations": details,
                "started_at": run_started.isoformat(),
                "ended_at": ended_at,
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
                "evidence": {"version": ael_evidence.EVIDENCE_VERSION, "count": 1, "status_counts": {"pass": 0, "fail": 1, "info": 0}},
                "stage_execution": _stage_execution_summary(until_stage, preflight_enabled=False),
            }
            _write_json(run_paths.result, result)
            meta["ended_at"] = ended_at
            meta["termination"] = RunTermination.FAIL
            _write_json(run_paths.meta, meta)
            workflow_archive.append_event(
                {
                    **archive_base,
                    **workflow_archive.runtime_event(
                        action="run_finished",
                        status="failed",
                        stage=until_stage,
                        extra={
                            "stage_execution": result["stage_execution"],
                            "result": {
                                "ok": False,
                                "termination": RunTermination.FAIL,
                                "failed_step": "check_meter_reachability",
                                "error_summary": error_summary,
                            },
                            "artifacts": {
                                "run_root": str(run_paths.root),
                                "meta": str(run_paths.meta),
                                "result": str(run_paths.result),
                                "evidence": str(evidence_path),
                            },
                        },
                    ),
                },
                run_root=run_paths.root,
            )
            return (6, run_paths) if return_paths else 6

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
    preflight_enabled = preflight_step is not None
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
            workflow_archive.append_event(
                {
                    **archive_base,
                    **workflow_archive.runtime_event(
                        action="run_finished",
                        status="failed",
                        stage=until_stage,
                        extra={
                            "stage_execution": _stage_execution_summary(until_stage, preflight_enabled=preflight_enabled),
                            "result": {
                                "ok": False,
                                "termination": RunTermination.FAIL,
                                "failed_step": "build",
                                "error_summary": "no build artifacts found",
                            },
                            "artifacts": {
                                "run_root": str(run_paths.root),
                                "meta": str(run_paths.meta),
                                "result": str(run_paths.result),
                                "evidence": str(evidence_path),
                            },
                        },
                    ),
                },
                run_root=run_paths.root,
            )
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
    plan["stage_execution"] = _stage_execution_summary(until_stage, preflight_enabled=preflight_enabled)
    plan["stages"] = ["plan", "pre-flight", "run", "check", "report"]

    registry = AdapterRegistry()
    runner_plan = dict(plan)
    runner_plan["steps"] = _filter_plan_steps_by_stage(plan_steps, until_stage)
    runner_result = run_plan(runner_plan, Path(run_paths.root), registry)
    if until_stage == "run-exit":
        return (0, run_paths) if return_paths else 0
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
        "stage_execution": _stage_execution_summary(until_stage, preflight_enabled=preflight_enabled),
    }
    if not result["ok"]:
        verify_failure = _verify_failure_observations(runner_result)
        if verify_failure.get("verify_substage"):
            result["verify_substage"] = verify_failure.get("verify_substage")
        if verify_failure.get("failure_class"):
            result["failure_class"] = verify_failure.get("failure_class")
        if isinstance(verify_failure.get("observations"), dict) and verify_failure.get("observations"):
            result["observations"] = verify_failure.get("observations")
    if result["ok"]:
        flash_info = _read_json(run_paths.flash_json)
        verify_result = _read_json((result.get("json") or {}).get("verify_result"))
        selected_ssid = None
        if isinstance(verify_result, dict):
            selected_ssid = verify_result.get("ssid") or verify_result.get("ap_ssid")
        validation_summary = _build_validation_summary(
            run_id=run_paths.run_id,
            board_cfg=board_cfg,
            test_path=test_path,
            run_result_path=str(run_paths.result),
            result=result,
            flash_info=flash_info,
            evidence_payload=evidence_payload,
            instrument_id=instrument_id,
            instrument_host=instrument_host,
            instrument_port=instrument_port,
            instrument_communication=instrument_communication,
            instrument_capability_surfaces=instrument_capability_surfaces,
            probe_instance_id=probe_instance_id,
            probe_type=probe_type,
            probe_host=probe_host,
            probe_port=probe_port,
            probe_communication=probe_communication,
            probe_capability_surfaces=probe_capability_surfaces,
            selected_ssid=selected_ssid,
            connection_setup=conn_setup,
        )
        last_known_good_setup = _build_last_known_good_setup(
            run_id=run_paths.run_id,
            board_cfg=board_cfg,
            test_path=test_path,
            flash_info=flash_info,
            instrument_id=instrument_id,
            instrument_host=instrument_host,
            instrument_port=instrument_port,
            instrument_communication=instrument_communication,
            instrument_capability_surfaces=instrument_capability_surfaces,
            probe_instance_id=probe_instance_id,
            probe_type=probe_type,
            probe_host=probe_host,
            probe_port=probe_port,
            probe_communication=probe_communication,
            probe_capability_surfaces=probe_capability_surfaces,
            selected_ssid=selected_ssid,
            connection_setup=conn_setup,
            result=result,
        )
        current_setup = _build_current_setup(
            flash_info=flash_info,
            instrument_id=instrument_id,
            instrument_host=instrument_host,
            instrument_port=instrument_port,
            instrument_communication=instrument_communication,
            instrument_capability_surfaces=instrument_capability_surfaces,
            probe_instance_id=probe_instance_id,
            probe_type=probe_type,
            probe_host=probe_host,
            probe_port=probe_port,
            probe_communication=probe_communication,
            probe_capability_surfaces=probe_capability_surfaces,
            selected_ssid=selected_ssid,
            connection_setup=conn_setup,
        )
        result["validation_summary"] = validation_summary
        result["last_known_good_setup"] = last_known_good_setup
        result["current_setup"] = current_setup
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

    workflow_archive.append_event(
        {
            **archive_base,
            **workflow_archive.runtime_event(
                action="run_finished",
                status="completed" if result["ok"] else "failed",
                stage=until_stage,
                extra={
                    "stage_execution": result.get("stage_execution"),
                    "result": {
                        "ok": result.get("ok"),
                        "termination": termination,
                        "failed_step": failed_step,
                        "error_summary": result.get("error_summary"),
                    },
                    "artifacts": {
                        "run_root": str(run_paths.root),
                        "meta": str(run_paths.meta),
                        "result": str(run_paths.result),
                        "run_plan": str(Path(run_paths.artifacts_dir) / "run_plan.json"),
                        "runner_result": str(Path(run_paths.artifacts_dir) / "result.json"),
                        "evidence": str(evidence_path),
                        "logs": result.get("logs"),
                    },
                },
            ),
        },
        run_root=run_paths.root,
    )

    if result["ok"]:
        print("PASS: Run verified")
        _print_success_summary(
            result.get("validation_summary", {}),
            result.get("last_known_good_setup", {}),
            result.get("current_setup", {}),
        )
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
