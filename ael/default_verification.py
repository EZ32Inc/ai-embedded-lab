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
from ael import inventory as inventory_view
from ael import strategy_resolver
from ael.config_resolver import resolve_control_instrument_config, resolve_control_instrument_instance
from ael.adapters import preflight
from ael.instruments import provision as instrument_provision
from ael.pipeline import _extract_verify_result_details, _normalize_probe_cfg, _simple_yaml_load, run_pipeline
from ael.probe_binding import empty_probe_binding, load_probe_binding
from ael.test_plan_schema import extract_plan_metadata
from ael.verification_model import VerificationSuite, VerificationTask, VerificationWorker
from ael.verification_model import _failure_summary as _worker_failure_summary
from ael.verification_model import summarize_resource_keys, summarize_worker_health


DEFAULT_CONFIG_PATH = ael_paths.repo_root() / "configs" / "default_verification_setting.yaml"


def _default_payload() -> Dict[str, Any]:
    return {"version": 1, "mode": "none"}


def _infer_instrument_condition(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
    condition = str(result.get("instrument_condition") or observations.get("instrument_condition") or "").strip()
    if condition:
        return condition
    failure_class = str(result.get("failure_class") or observations.get("failure_class") or "").strip()
    verify_substage = str(result.get("verify_substage") or observations.get("verify_substage") or "").strip()
    if failure_class == "network_meter_reachability":
        return "instrument_unreachable"
    if failure_class == "network_meter_tcp":
        return "instrument_transport_unavailable"
    if failure_class == "network_meter_api":
        return "instrument_api_unavailable"
    if verify_substage == "instrument.signature" or failure_class.startswith("instrument_"):
        return "instrument_verify_failed"
    return ""


def _infer_failure_scope(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    observations = result.get("observations") if isinstance(result.get("observations"), dict) else {}
    scope = str(result.get("failure_scope") or observations.get("failure_scope") or "").strip()
    if scope:
        return scope
    condition = _infer_instrument_condition(result)
    failure_class = str(result.get("failure_class") or observations.get("failure_class") or "").strip()
    verify_substage = str(result.get("verify_substage") or observations.get("verify_substage") or "").strip()
    if condition in ("instrument_unreachable", "instrument_transport_unavailable", "instrument_api_unavailable"):
        return "bench"
    if condition == "instrument_verify_failed" or verify_substage == "instrument.signature" or failure_class.startswith("instrument_"):
        return "verify"
    return ""


def _degraded_instrument_policy(result: Dict[str, Any]) -> Dict[str, Any]:
    condition = _infer_instrument_condition(result)
    scope = _infer_failure_scope(result)
    policy = {
        "policy_class": "",
        "retryable": False,
        "max_attempts": 1,
        "backoff_s": 0.0,
        "failure_scope": scope,
    }
    if condition == "instrument_unreachable":
        policy["policy_class"] = "bench_degraded_fail_fast"
    elif condition in ("instrument_transport_unavailable", "instrument_api_unavailable"):
        policy["policy_class"] = "bench_degraded_retry_once"
        policy["retryable"] = True
        policy["max_attempts"] = 2
        policy["backoff_s"] = 1.0
    elif condition == "instrument_verify_failed":
        policy["policy_class"] = "verify_no_retry"
    return policy


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


def _metadata_explanation(metadata: Dict[str, Any]) -> Dict[str, str | None]:
    test_kind = str(metadata.get("test_kind") or "").strip()
    requires = metadata.get("requires") if isinstance(metadata.get("requires"), dict) else {}
    if test_kind == "instrument_specific":
        return {
            "verification_mode_summary": "instrument-side measurement path",
            "requires_summary": "requires instrument-side measurement and no mailbox dependency",
        }
    if test_kind == "baremetal_mailbox":
        mailbox_required = requires.get("mailbox") is True
        return {
            "verification_mode_summary": "bare-metal mailbox verification",
            "requires_summary": "requires mailbox-backed DUT result path" if mailbox_required else "mailbox optional",
        }
    return {
        "verification_mode_summary": None,
        "requires_summary": None,
    }


def _load_instrument_instance_type(repo_root: Path, instrument_id: str | None) -> str | None:
    instance_id = str(instrument_id or "").strip()
    if not instance_id:
        return None
    for root in (repo_root, ael_paths.repo_root()):
        path = Path(root) / "configs" / "instrument_instances" / f"{instance_id}.yaml"
        if not path.exists():
            continue
        raw = _simple_yaml_load(str(path))
        instance = raw.get("instance", {}) if isinstance(raw, dict) else {}
        if not isinstance(instance, dict):
            continue
        type_id = str(instance.get("type") or raw.get("type") or "").strip()
        if type_id:
            return type_id
    if instance_id == "esp32s3_dev_c_meter":
        return "esp32_meter"
    return None


def _supported_instrument_advisory(
    supported_instruments: List[str] | None,
    *,
    selected_instrument_id: str | None,
    selected_instrument_type: str | None,
) -> Dict[str, Any] | None:
    declared = [item for item in (supported_instruments or []) if isinstance(item, str) and item.strip()]
    if not declared:
        return None
    if not selected_instrument_type:
        return {
            "status": "selection_unresolved",
            "selected_instrument_id": selected_instrument_id,
            "selected_instrument_type": None,
            "declared_supported_instruments": declared,
            "summary": "supported instruments declared, but no selected instrument type was resolved",
        }
    status = "declared_supported" if selected_instrument_type in declared else "declared_unsupported"
    summary = (
        f"selected instrument type {selected_instrument_type} is declared supported"
        if status == "declared_supported"
        else f"selected instrument type {selected_instrument_type} is not in declared support set"
    )
    return {
        "status": status,
        "selected_instrument_id": selected_instrument_id,
        "selected_instrument_type": selected_instrument_type,
        "declared_supported_instruments": declared,
        "summary": summary,
    }


def _schema_advisory_payload_from_test(repo_root: Path, test_path: str) -> Dict[str, Any]:
    raw = _load_text_payload(Path(test_path))
    if not isinstance(raw, dict):
        return {}
    metadata = extract_plan_metadata(raw)
    explanation = _metadata_explanation(metadata)
    instrument_cfg = raw.get("instrument") if isinstance(raw.get("instrument"), dict) else {}
    instrument_id = str(instrument_cfg.get("id") or "").strip() or None
    instrument_type = _load_instrument_instance_type(repo_root, instrument_id)
    advisory = _supported_instrument_advisory(
        metadata.get("supported_instruments"),
        selected_instrument_id=instrument_id,
        selected_instrument_type=instrument_type,
    )
    items: List[str] = []
    for key in ("verification_mode_summary", "requires_summary"):
        value = str(explanation.get(key) or "").strip()
        if value:
            items.append(value)
    if isinstance(advisory, dict):
        summary = str(advisory.get("summary") or "").strip()
        if summary:
            items.append(summary)
    status = str(advisory.get("status") or "").strip() if isinstance(advisory, dict) else ""
    warnings: List[str] = []
    if status == "declared_unsupported":
        warnings.append(str(advisory.get("summary") or "selected instrument is not in declared support set"))
    return {
        "plan_schema_kind": "structured" if metadata.get("schema_version") not in (None, "", "legacy") else "legacy",
        "schema_version": metadata.get("schema_version"),
        "test_kind": metadata.get("test_kind"),
        "supported_instruments": metadata.get("supported_instruments"),
        "supported_instrument_advisory": advisory,
        "schema_advisories": items,
        "schema_warning_messages": warnings,
    }


def _schema_advisory_payload(repo_root: Path, board: str, test: str) -> Dict[str, Any]:
    fallback = _schema_advisory_payload_from_test(repo_root, test)
    try:
        described = inventory_view.describe_test(board_id=board, test_path=test, repo_root=repo_root)
    except Exception:
        described = {}
    if not isinstance(described, dict) or not described.get("ok"):
        return fallback
    test_payload = described.get("test") if isinstance(described.get("test"), dict) else {}
    advisory = test_payload.get("supported_instrument_advisory") if isinstance(test_payload.get("supported_instrument_advisory"), dict) else None
    items: List[str] = []
    for key in ("verification_mode_summary", "requires_summary"):
        value = str(test_payload.get(key) or "").strip()
        if value:
            items.append(value)
    if isinstance(advisory, dict):
        summary = str(advisory.get("summary") or "").strip()
        if summary:
            items.append(summary)
    status = str(advisory.get("status") or "").strip() if isinstance(advisory, dict) else ""
    warnings: List[str] = []
    if status == "declared_unsupported":
        warnings.append(str(advisory.get("summary") or "selected instrument is not in declared support set"))
    payload = {
        "plan_schema_kind": "structured" if test_payload.get("schema_version") not in (None, "", "legacy") else "legacy",
        "schema_version": test_payload.get("schema_version"),
        "test_kind": test_payload.get("test_kind"),
        "supported_instruments": test_payload.get("supported_instruments"),
        "supported_instrument_advisory": advisory,
        "schema_advisories": items,
        "schema_warning_messages": warnings,
    }
    fallback_advisory = fallback.get("supported_instrument_advisory") if isinstance(fallback.get("supported_instrument_advisory"), dict) else None
    if (
        isinstance(fallback_advisory, dict)
        and str(fallback_advisory.get("status") or "").strip() in {"declared_supported", "declared_unsupported"}
        and str((advisory or {}).get("status") or "").strip() == "selection_unresolved"
    ):
        payload.update({k: v for k, v in fallback.items() if v not in (None, "", [], {})})
    return payload


def _summarize_schema_advisories(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "structured_step_count": 0,
        "legacy_step_count": 0,
        "test_kind_counts": {},
        "supported_instrument_status_counts": {},
        "warning_messages": [],
        "instrument_specific_steps": [],
    }
    seen_warnings: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        schema_kind = str(result.get("plan_schema_kind") or "").strip()
        if schema_kind == "structured":
            summary["structured_step_count"] += 1
        elif schema_kind == "legacy":
            summary["legacy_step_count"] += 1
        test_kind = str(result.get("test_kind") or "").strip()
        if test_kind:
            summary["test_kind_counts"][test_kind] = int(summary["test_kind_counts"].get(test_kind, 0)) + 1
            if test_kind == "instrument_specific":
                summary["instrument_specific_steps"].append(str(item.get("name") or ""))
        advisory = result.get("supported_instrument_advisory") if isinstance(result.get("supported_instrument_advisory"), dict) else {}
        advisory_status = str(advisory.get("status") or "").strip()
        if advisory_status:
            counts = summary["supported_instrument_status_counts"]
            counts[advisory_status] = int(counts.get(advisory_status, 0)) + 1
        warnings = result.get("schema_warning_messages") if isinstance(result.get("schema_warning_messages"), list) else []
        for message in warnings:
            text = str(message or "").strip()
            if not text or text in seen_warnings:
                continue
            seen_warnings.add(text)
            summary["warning_messages"].append(text)
    summary["instrument_specific_steps"] = sorted(item for item in summary["instrument_specific_steps"] if item)
    return summary


def _print_schema_advisory_summary(lock: threading.Lock, summary: Dict[str, Any]) -> None:
    structured = int(summary.get("structured_step_count", 0))
    legacy = int(summary.get("legacy_step_count", 0))
    _log_line(lock, f"[SUMMARY] schema structured={structured} legacy={legacy}")
    test_kind_counts = summary.get("test_kind_counts") if isinstance(summary.get("test_kind_counts"), dict) else {}
    if test_kind_counts:
        parts = [f"{name}={test_kind_counts[name]}" for name in sorted(test_kind_counts)]
        _log_line(lock, f"[SUMMARY] schema_test_kinds {' '.join(parts)}")
    status_counts = summary.get("supported_instrument_status_counts") if isinstance(summary.get("supported_instrument_status_counts"), dict) else {}
    if status_counts:
        parts = [f"{name}={status_counts[name]}" for name in sorted(status_counts)]
        _log_line(lock, f"[SUMMARY] schema_instrument_support {' '.join(parts)}")
    warnings = summary.get("warning_messages") if isinstance(summary.get("warning_messages"), list) else []
    if warnings:
        _log_line(lock, f"[SUMMARY] schema_warnings count={len(warnings)}")


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
            "test": "tests/plans/rp2040_gpio_signature.json",
        }
    if key in ("esp32s3_then_rp2040", "esp32s3_gpio_then_rp2040"):
        return {
            "version": 1,
            "mode": "sequence",
            "execution_policy": {"kind": "serial"},
            "stop_on_fail": True,
            "steps": [
                {
                    "board": "esp32s3_devkit",
                    "test": "tests/plans/esp32s3_gpio_signature_with_meter.json",
                },
                {
                    "board": "rp2040_pico",
                    "test": "tests/plans/rp2040_gpio_signature.json",
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


def _load_test_payload(test_path: str | None) -> Dict[str, Any]:
    if not test_path:
        return {}
    path = Path(test_path)
    if not path.exists():
        return {}
    return _load_text_payload(path)


def _canonical_test_name(test_path: str | None) -> str:
    payload = _load_test_payload(test_path)
    name = str(payload.get("name") or "").strip() if isinstance(payload, dict) else ""
    if name:
        return name
    return Path(str(test_path or "")).stem or "unknown_test"


def _validate_sequence_steps(repo_root: Path, setting: Dict[str, Any]) -> Tuple[bool, str]:
    steps = setting.get("steps", [])
    if not isinstance(steps, list) or not steps:
        return False, "sequence mode requires non-empty steps"
    inventory_payload = inventory_view.build_inventory(repo_root)
    valid_pairs = {
        (
            str(dut.get("dut_id") or "").strip(),
            _resolve_path(repo_root, str(test.get("path") or "").strip()) or str(test.get("path") or "").strip(),
        )
        for dut in inventory_payload.get("duts", [])
        if isinstance(dut, dict)
        for test in dut.get("tests", [])
        if isinstance(test, dict)
    }
    forbidden_fields = ("name", "probe", "instrument_instance")
    for idx, raw_step in enumerate(steps, start=1):
        if not isinstance(raw_step, dict):
            return False, f"step {idx} must be an object"
        board = str(raw_step.get("board") or "").strip()
        test = _resolve_path(repo_root, raw_step.get("test"))
        if not board or not test:
            return False, f"step {idx} requires board and test"
        if (board, test) not in valid_pairs:
            test_payload = _load_test_payload(test)
            test_board = str(test_payload.get("board") or "").strip() if isinstance(test_payload, dict) else ""
            board_raw = _resolve_board_raw(repo_root, board)
            if not (test_board == board and board_raw):
                return False, f"step {idx} references non-DUT test board={board} test={test}"
        bad = [field for field in forbidden_fields if raw_step.get(field) not in (None, "")]
        if bad:
            return False, f"step {idx} must not redefine DUT test identity/setup fields: {', '.join(bad)}"
    return True, ""


def _resolve_step_probe_binding(repo_root: Path, step: Dict[str, Any]) -> Tuple[Dict[str, Any], str | None]:
    config_root = repo_root if (repo_root / "configs").exists() else ael_paths.repo_root()
    instance_id = str(step.get("instrument_instance") or "").strip() or resolve_control_instrument_instance(
        str(config_root),
        args=None,
        board_id=str(step.get("board") or ""),
    )
    probe_path = _resolve_path(
        config_root,
        step.get("probe"),
        resolve_control_instrument_config(str(config_root), args=None, board_id=str(step.get("board") or "")),
    )
    if not instance_id and not probe_path:
        binding = empty_probe_binding()
        return binding.raw, binding.config_path
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


def _local_instrument_interface_path(repo_root: Path, board: str | None, test_path: str | None) -> str:
    board_id = str(board or "").strip()
    if not board_id:
        return ""
    board_raw = _resolve_board_raw(repo_root, board_id)
    board_cfg = board_raw.get("board", {}) if isinstance(board_raw.get("board"), dict) else {}
    if test_path:
        test_raw = _load_text_payload(Path(test_path))
        if isinstance(test_raw, dict):
            instrument_id, _tcp_cfg, _manifest = strategy_resolver.resolve_instrument_context(test_raw, board_cfg)
            if str(instrument_id or "").strip() == "esp32s3_dev_c_meter":
                return "meter_native_api"
    probe_raw, probe_path = _resolve_step_probe_binding(repo_root, {"board": board_id, "test": test_path})
    probe_cfg = _normalize_probe_cfg(probe_raw)
    if probe_path or str(probe_cfg.get("host") or "").strip():
        try:
            config_root = repo_root if (repo_root / "configs").exists() else ael_paths.repo_root()
            instance_id = resolve_control_instrument_instance(
                str(config_root),
                args=None,
                board_id=board_id,
            )
            if instance_id:
                binding = load_probe_binding(config_root, instance_id=instance_id)
            else:
                binding = load_probe_binding(config_root, probe_path=probe_path)
            if str(binding.type_id or "").strip() == "esp32jtag":
                return "jtag_native_api"
        except Exception:
            pass
        return "control_instrument_native_api"
    return ""


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
        timeout_s=instrument_provision.RUN_METER_GUARD_TIMEOUT_S,
    )


def _run_single(repo_root: Path, step: Dict[str, Any], output_mode: str) -> Tuple[int, Dict[str, Any]]:
    board = step.get("board")
    test = _resolve_path(repo_root, step.get("test"))
    if not board or not test:
        return 2, {"ok": False, "error": "single_run requires board and test"}
    local_interface_path = _local_instrument_interface_path(repo_root, str(board), test)
    schema_payload = _schema_advisory_payload(repo_root, str(board), str(test))
    for item in schema_payload.get("schema_warning_messages") or []:
        print(f"default_verification: warning - {item}")
    meter_attempts = 0
    while True:
        try:
            meter_attempts += 1
            _ensure_step_meter_reachable(repo_root, str(board), test)
            break
        except Exception as exc:
            print(f"default_verification: {exc}")
            details = getattr(exc, "details", {})
            out = {"ok": False, "error": str(exc), "error_summary": str(exc)}
            if isinstance(details, dict) and details:
                out["observations"] = dict(details)
                if details.get("failure_class"):
                    out["failure_class"] = details.get("failure_class")
            instrument_condition = _infer_instrument_condition(out)
            if instrument_condition:
                out["instrument_condition"] = instrument_condition
                if isinstance(out.get("observations"), dict):
                    out["observations"].setdefault("instrument_condition", instrument_condition)
            failure_scope = _infer_failure_scope(out)
            if failure_scope:
                out["failure_scope"] = failure_scope
                if isinstance(out.get("observations"), dict):
                    out["observations"].setdefault("failure_scope", failure_scope)
            if local_interface_path:
                out["local_instrument_interface_path"] = local_interface_path
            out.update({k: v for k, v in schema_payload.items() if v not in (None, "", [], {})})
            policy = _degraded_instrument_policy(out)
            out["degraded_instrument_policy"] = policy
            out["retry_summary"] = {
                "meter_guard_attempts": meter_attempts,
                "meter_guard_retries_used": max(0, meter_attempts - 1),
            }
            if policy.get("retryable") and meter_attempts < int(policy.get("max_attempts") or 1):
                backoff_s = float(policy.get("backoff_s") or 0.0)
                print(
                    "default_verification: degraded instrument retry "
                    f"{meter_attempts}/{int(policy.get('max_attempts') or 1) - 1} "
                    f"after {backoff_s:.1f}s"
                )
                if backoff_s > 0:
                    time.sleep(backoff_s)
                continue
            return 2, out
    code = run_pipeline(
        probe_path=None,
        board_arg=str(board),
        test_path=str(test),
        wiring=None,
        output_mode=output_mode,
        return_paths=True,
    )
    if isinstance(code, tuple) and len(code) == 2:
        exit_code, payload = code
        if isinstance(payload, dict):
            out = {"ok": int(exit_code) == 0}
            if local_interface_path:
                out["local_instrument_interface_path"] = local_interface_path
            out.update({k: v for k, v in schema_payload.items() if v not in (None, "", [], {})})
            if not bool(out["ok"]):
                for key in ("error", "error_summary", "verify_substage", "failure_class", "instrument_condition", "observations"):
                    if key in payload and payload.get(key) not in (None, "", {}, []):
                        out[key] = payload.get(key)
                if not any(key in out for key in ("error_summary", "verify_substage", "failure_class", "instrument_condition", "observations")):
                    for key, value in _extract_verify_result_details(payload).items():
                        if key not in out and value not in (None, "", {}, []):
                            out[key] = value
                instrument_condition = _infer_instrument_condition(out)
                if instrument_condition and "instrument_condition" not in out:
                    out["instrument_condition"] = instrument_condition
                if instrument_condition and isinstance(out.get("observations"), dict):
                    out["observations"].setdefault("instrument_condition", instrument_condition)
                failure_scope = _infer_failure_scope(out)
                if failure_scope:
                    out["failure_scope"] = failure_scope
                    if isinstance(out.get("observations"), dict):
                        out["observations"].setdefault("failure_scope", failure_scope)
                policy = _degraded_instrument_policy(out)
                if policy.get("policy_class"):
                    out["degraded_instrument_policy"] = policy
            return int(exit_code), out
        out = {"ok": int(exit_code) == 0}
        if local_interface_path:
            out["local_instrument_interface_path"] = local_interface_path
        out.update({k: v for k, v in schema_payload.items() if v not in (None, "", [], {})})
        if not bool(out["ok"]) and hasattr(payload, "artifacts_dir"):
            details = _extract_verify_result_details(
                {
                    "json": {
                        "verify_result": str(Path(payload.artifacts_dir) / "verify_result.json"),
                    }
                }
            )
            for key, value in details.items():
                if value not in (None, "", {}, []):
                    out[key] = value
            instrument_condition = _infer_instrument_condition(out)
            if instrument_condition and "instrument_condition" not in out:
                out["instrument_condition"] = instrument_condition
            if instrument_condition and isinstance(out.get("observations"), dict):
                out["observations"].setdefault("instrument_condition", instrument_condition)
            failure_scope = _infer_failure_scope(out)
            if failure_scope:
                out["failure_scope"] = failure_scope
                if isinstance(out.get("observations"), dict):
                    out["observations"].setdefault("failure_scope", failure_scope)
            policy = _degraded_instrument_policy(out)
            if policy.get("policy_class"):
                out["degraded_instrument_policy"] = policy
        return int(exit_code), out
    out = {"ok": int(code) == 0}
    if local_interface_path:
        out["local_instrument_interface_path"] = local_interface_path
    out.update({k: v for k, v in schema_payload.items() if v not in (None, "", [], {})})
    return int(code), out


def _normalized_step(setting: Dict[str, Any], raw_step: Dict[str, Any], idx: int) -> Dict[str, Any]:
    step = dict(raw_step) if isinstance(raw_step, dict) else {}
    test_path = _resolve_path(ael_paths.repo_root(), step.get("test"))
    step["name"] = _canonical_test_name(test_path)
    step["action"] = str(step.get("action") or "single_run").strip().lower()
    return step


def _execution_policy(setting: Dict[str, Any]) -> Dict[str, Any]:
    raw = setting.get("execution_policy", {}) if isinstance(setting.get("execution_policy"), dict) else {}
    kind = str(raw.get("kind") or "parallel").strip().lower()
    if kind not in ("parallel", "serial"):
        kind = "parallel"
    return {"kind": kind}


def _suite_from_setting(setting: Dict[str, Any]) -> VerificationSuite:
    steps = setting.get("steps", [])
    tasks: List[VerificationTask] = []
    if isinstance(steps, list):
        for idx, raw_step in enumerate(steps, start=1):
            step = _normalized_step(setting, raw_step, idx)
            tasks.append(
                VerificationTask(
                    name=str(step.get("name") or f"step_{idx:02d}"),
                    board=str(step.get("board") or ""),
                    action=str(step.get("action") or "single_run"),
                    config={k: v for k, v in step.items() if k not in ("name", "board", "action")},
                )
            )
    return VerificationSuite(
        name=str(setting.get("suite_name") or "default_verification"),
        tasks=tasks,
        execution_policy=_execution_policy(setting),
    )


def _log_line(lock: threading.Lock, message: str) -> None:
    with lock:
        print(message, flush=True)


def _run_step_action(repo_root: Path, step: Dict[str, Any], output_mode: str) -> Tuple[int, Dict[str, Any]]:
    if str(step.get("action") or "single_run").strip().lower() == "preflight_only":
        return _run_preflight_only(repo_root, step)
    return _run_single(repo_root, step, output_mode)


def _worker_for_task(
    repo_root: Path,
    task: VerificationTask,
    output_mode: str,
    max_iterations: int,
    stop_after_failure: bool,
    log_lock: threading.Lock,
) -> VerificationWorker:
    return VerificationWorker(
        task=task,
        repo_root=repo_root,
        output_mode=output_mode,
        runner=_run_step_action,
        iteration_limit=max_iterations,
        stop_after_failure=stop_after_failure,
        log_fn=lambda message: _log_line(log_lock, message),
        resource_keys=_task_resource_keys(repo_root, task),
    )


def _task_resource_keys(repo_root: Path, task: VerificationTask) -> List[str]:
    step = task.step()
    keys = [f"dut:{task.board}"]

    probe_raw, probe_path = _resolve_step_probe_binding(repo_root, step)
    probe_cfg = _normalize_probe_cfg(probe_raw)
    probe_host = str(probe_cfg.get("host") or "").strip()
    probe_port = probe_cfg.get("gdb_port")
    if probe_host and probe_port is not None:
        keys.append(f"probe:{probe_host}:{probe_port}")
    elif probe_path:
        keys.append(f"probe_path:{probe_path}")

    board_raw = _resolve_board_raw(repo_root, task.board)
    board_cfg = board_raw.get("board", {}) if isinstance(board_raw.get("board"), dict) else {}
    flash_cfg = board_cfg.get("flash", {}) if isinstance(board_cfg.get("flash"), dict) else {}
    flash_port = str(flash_cfg.get("port") or "").strip()
    if flash_port:
        keys.append(f"serial:{flash_port}")

    test_path = _resolve_path(repo_root, step.get("test"))
    if test_path:
        test_raw = _load_text_payload(Path(test_path))
        if isinstance(test_raw, dict):
            instrument_id, tcp_cfg, _manifest = strategy_resolver.resolve_instrument_context(test_raw, board_cfg)
            host = str((tcp_cfg or {}).get("host") or "").strip()
            port = (tcp_cfg or {}).get("port")
            if instrument_id and host and port is not None:
                keys.append(f"instrument:{instrument_id}:{host}:{port}")

    deduped: List[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _task_resource_summary(repo_root: Path, task: VerificationTask) -> Dict[str, Any]:
    return summarize_resource_keys(_task_resource_keys(repo_root, task))


def _print_worker_totals(lock: threading.Lock, workers: List[Dict[str, Any]]) -> None:
    _log_line(lock, "[SUMMARY]")
    for worker in workers:
        line = f"{worker.get('name')}: {worker.get('pass_count', 0)}/{worker.get('completed_iterations', 0)} PASS"
        if not bool(worker.get("ok", False)):
            results = worker.get("results", [])
            last = results[-1] if isinstance(results, list) and results else {}
            detail = _worker_failure_summary(last.get("result") if isinstance(last, dict) else {})
            if detail:
                line += f" {detail}"
        _log_line(lock, line)
    health = summarize_worker_health(workers)
    _log_line(
        lock,
        "[SUMMARY] health pass_count="
        f"{health.get('total_pass_count', 0)} fail_count={health.get('total_fail_count', 0)}",
    )
    local_paths = health.get("local_instrument_interface_path_counts")
    if isinstance(local_paths, dict) and local_paths:
        parts = [f"{name}={local_paths[name]}" for name in sorted(local_paths)]
        _log_line(lock, f"[SUMMARY] local_instrument_interface_paths {' '.join(parts)}")
    counts = health.get("instrument_condition_counts")
    if isinstance(counts, dict) and counts:
        parts = [f"{name}={counts[name]}" for name in sorted(counts)]
        _log_line(lock, f"[SUMMARY] degraded_instruments {' '.join(parts)}")
    results = [item for worker in workers for item in worker.get("results", [])]
    _print_schema_advisory_summary(lock, _summarize_schema_advisories(results))


def _run_parallel_suite_once(
    repo_root: Path,
    suite: VerificationSuite,
    output_mode: str,
) -> Tuple[int, Dict[str, Any]]:
    log_lock = threading.Lock()
    workers: List[Dict[str, Any]] = []
    _log_line(log_lock, f"default_verification: selected DUT tests: {', '.join(task.name for task in suite.tasks)}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(suite.tasks))) as executor:
        futures = [
            executor.submit(_worker_for_task(repo_root, task, output_mode, 1, False, log_lock).run)
            for task in suite.tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            workers.append(future.result().to_dict())

    _print_worker_totals(log_lock, workers)
    optional_names = {task.name for task in suite.tasks if task.config.get("optional")}
    results = [item for worker in workers for item in worker.get("results", [])]
    failed = next((item for item in results if not bool(item.get("ok", False)) and item.get("name") not in optional_names), None)
    code = int(failed.get("code", 0)) if isinstance(failed, dict) else 0
    ok = failed is None
    return code, {
        "ok": ok,
        "mode": "sequence",
        "suite": {"name": suite.name, "tasks": [task.name for task in suite.tasks]},
        "execution_policy": {"kind": suite.execution_policy.get("kind", "parallel"), "iterations_per_worker": 1},
        "selected_dut_tests": [task.name for task in suite.tasks],
        "optional_steps": sorted(optional_names),
        "workers": workers,
        "results": results,
        "schema_advisory_summary": _summarize_schema_advisories(results),
    }


def _run_serial_suite_once(
    repo_root: Path,
    setting: Dict[str, Any],
    suite: VerificationSuite,
    output_mode: str,
) -> Tuple[int, Dict[str, Any]]:
    stop_on_fail = bool(setting.get("stop_on_fail", True))
    overall_ok = True
    last_code = 0
    results: List[Dict[str, Any]] = []
    print(f"default_verification: selected DUT tests: {', '.join(task.name for task in suite.tasks)}")

    for task in suite.tasks:
        optional = bool(task.config.get("optional", False))
        code, result = _run_step_action(repo_root, task.step(), output_mode)
        ok = code == 0
        results.append({"name": task.name, "board": task.board, "code": code, "ok": ok, "optional": optional, "result": result})
        if not ok:
            if optional:
                print(f"default_verification: {task.name} failed but is optional — not counted")
            else:
                overall_ok = False
                last_code = code
                if stop_on_fail:
                    break

    return (0 if overall_ok else last_code or 1), {
        "ok": overall_ok,
        "mode": "sequence",
        "suite": {"name": suite.name, "tasks": [task.name for task in suite.tasks]},
        "execution_policy": {"kind": suite.execution_policy.get("kind", "serial"), "iterations_per_worker": 1},
        "selected_dut_tests": [task.name for task in suite.tasks],
        "results": results,
        "schema_advisory_summary": _summarize_schema_advisories(results),
    }


def _run_parallel_repeat_until_fail(
    repo_root: Path,
    suite: VerificationSuite,
    output_mode: str,
    limit: int,
) -> Tuple[int, Dict[str, Any]]:
    log_lock = threading.Lock()
    workers: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(suite.tasks))) as executor:
        futures = [
            executor.submit(_worker_for_task(repo_root, task, output_mode, limit, True, log_lock).run)
            for task in suite.tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            workers.append(future.result().to_dict())

    _print_worker_totals(log_lock, workers)
    optional_names = {task.name for task in suite.tasks if task.config.get("optional")}
    results = [item for worker in workers for item in worker.get("results", [])]
    failures = [item for item in results if not bool(item.get("ok", False)) and item.get("name") not in optional_names]
    first_failure = failures[0] if failures else None
    code = int(first_failure.get("code", 0)) if isinstance(first_failure, dict) else 0
    ok = first_failure is None
    payload: Dict[str, Any] = {
        "ok": ok,
        "mode": "repeat_until_fail",
        "suite": {"name": suite.name, "tasks": [task.name for task in suite.tasks]},
        "execution_policy": {"kind": suite.execution_policy.get("kind", "parallel"), "iterations_per_worker": limit, "stop_each_worker_on_failure": True},
        "selected_dut_tests": [task.name for task in suite.tasks],
        "optional_steps": sorted(optional_names),
        "requested_iterations_per_worker": limit,
        "workers": workers,
        "results": results,
        "health_summary": summarize_worker_health(workers),
        "schema_advisory_summary": _summarize_schema_advisories(results),
    }
    if first_failure is not None:
        first_result = first_failure.get("result") if isinstance(first_failure.get("result"), dict) else {}
        failure_scope = first_result.get("failure_scope") or _infer_failure_scope(first_result)
        instrument_condition = first_result.get("instrument_condition") or _infer_instrument_condition(first_result)
        payload["failure"] = {
            "step_name": first_failure.get("name"),
            "board": first_failure.get("board"),
            "iteration": first_failure.get("iteration"),
            "step_code": first_failure.get("code"),
            "failure_scope": failure_scope or None,
            "instrument_condition": instrument_condition or None,
            "reason": (
                first_result.get("error")
                or first_result.get("error_summary")
                if isinstance(first_result, dict)
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
        return code, {"ok": code == 0, "mode": mode, "selected_dut_tests": [], "results": results}

    if mode == "single_run":
        code, result = _run_single(repo_root, setting, output_mode)
        selected_test = _canonical_test_name(_resolve_path(repo_root, setting.get("test")))
        print(f"default_verification: selected DUT tests: {selected_test}")
        results.append({"name": selected_test, "code": code, "ok": code == 0, "result": result})
        return code, {"ok": code == 0, "mode": mode, "selected_dut_tests": [selected_test], "results": results}

    if mode == "sequence":
        ok, error = _validate_sequence_steps(repo_root, setting)
        if not ok:
            return 2, {"ok": False, "mode": mode, "error": error}
        suite = _suite_from_setting(setting)
        if suite.execution_policy.get("kind") == "serial":
            return _run_serial_suite_once(repo_root, setting, suite, output_mode)
        return _run_parallel_suite_once(repo_root, suite, output_mode)

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
        ok, error = _validate_sequence_steps(ael_paths.repo_root(), setting)
        if not ok:
            return 2, {"ok": False, "mode": mode, "error": error}
        suite = _suite_from_setting(setting)
        if suite.execution_policy.get("kind") != "serial":
            repo_root = ael_paths.repo_root()
            return _run_parallel_repeat_until_fail(
                repo_root=repo_root,
                suite=suite,
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
