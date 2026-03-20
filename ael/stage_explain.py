from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ael.connection_model import build_connection_setup, render_connection_setup_text
from ael.pipeline import _simple_yaml_load
from ael.config_resolver import (
    resolve_control_instrument_config,
    resolve_control_instrument_instance,
)
from ael.instrument_metadata import resolve_capability_surface
from ael.probe_binding import empty_probe_binding, load_probe_binding
from ael.verification_model import summarize_resource_keys
from ael.strategy_resolver import (
    build_preflight_step,
    build_uart_step,
    build_verify_step,
    normalize_probe_cfg,
    resolve_control_instrument_override,
    resolve_build_stage,
    resolve_load_stage,
    resolve_run_strategy,
)
from ael.test_plan_schema import extract_plan_metadata
from ael.instruments.registry import InstrumentRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _resolved_schema_advisories(ctx: Dict[str, Any]) -> List[str]:
    resolved = ctx["resolved"]
    metadata = extract_plan_metadata(ctx["test_raw"])
    selected_instrument_id = ctx.get("probe_instance_id") or resolved.instrument_id
    selected_instrument_type = ctx.get("probe_type")
    if not selected_instrument_type and resolved.instrument_id:
        selected_instrument_type = _load_instrument_instance_type(REPO_ROOT, resolved.instrument_id) or (InstrumentRegistry().get(resolved.instrument_id) or {}).get("type")
    advisory = _supported_instrument_advisory(
        metadata.get("supported_instruments"),
        selected_instrument_id=selected_instrument_id,
        selected_instrument_type=selected_instrument_type,
    )
    items: List[str] = []
    explanation = _metadata_explanation(metadata)
    if explanation.get("verification_mode_summary"):
        items.append(str(explanation.get("verification_mode_summary")))
    if explanation.get("requires_summary"):
        items.append(str(explanation.get("requires_summary")))
    if isinstance(advisory, dict) and advisory.get("summary"):
        items.append(str(advisory.get("summary")))
    return items


def _control_instrument_selection(ctx: Dict[str, Any]) -> Dict[str, Any] | None:
    instance = ctx.get("probe_instance_id")
    config_path = ctx.get("probe_path")
    type_id = ctx.get("probe_type")
    communication = dict(ctx.get("probe_communication") or {})
    capability_surfaces = dict(ctx.get("probe_capability_surfaces") or {})
    if not any([instance, config_path, type_id, communication, capability_surfaces]):
        return None
    return {
        "config": config_path,
        "instance": instance,
        "type": type_id,
        "communication": communication,
        "capability_surfaces": capability_surfaces,
    }


def _selected_dut_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx.get("resolved")
    board_cfg = resolved.board_cfg if resolved is not None else {}
    ownership_kind = str(ctx.get("ownership_kind") or "board_owned").strip() or "board_owned"
    return {
        "id": board_id,
        "name": board_cfg.get("name") if isinstance(board_cfg, dict) else None,
        "target": board_cfg.get("target") if isinstance(board_cfg, dict) else None,
        "runtime_binding": "board_profile_driven" if ownership_kind == "board_owned" else "instrument_owned_plan",
    }


def _selected_board_profile_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx.get("resolved")
    board_cfg = resolved.board_cfg if resolved is not None else {}
    ownership_kind = str(ctx.get("ownership_kind") or "board_owned").strip() or "board_owned"
    return {
        "id": board_id,
        "name": board_cfg.get("name") if isinstance(board_cfg, dict) else None,
        "target": board_cfg.get("target") if isinstance(board_cfg, dict) else None,
        "config": ctx.get("board_path"),
        "role": "runtime_policy" if ownership_kind == "board_owned" else "instrument_plan_context",
    }


def _bench_selection_digest(payload: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    serial_port = payload.get("serial_port")
    if serial_port:
        items.append(f"serial:{serial_port}")
    selected_ap_ssid = payload.get("selected_ap_ssid")
    if selected_ap_ssid:
        items.append(f"ssid:{selected_ap_ssid}")
    instrument = payload.get("instrument")
    if isinstance(instrument, dict):
        inst_id = instrument.get("id")
        if inst_id:
            items.append(f"instrument_id:{inst_id}")
        communication = instrument.get("communication")
        endpoint = communication.get("endpoint") if isinstance(communication, dict) else None
        if endpoint:
            items.append(f"instrument_endpoint:{endpoint}")
    control = payload.get("controller") or payload.get("control_instrument")
    if isinstance(control, dict):
        instance = control.get("instance")
        if instance:
            items.append(f"controller_instance:{instance}")
            items.append(f"control_instrument_instance:{instance}")
        config_path = control.get("config")
        if config_path:
            items.append(f"controller_config:{config_path}")
            items.append(f"control_instrument_config:{config_path}")
    return items


def _selected_bench_resources_payload(ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx["resolved"]
    connection_setup = build_connection_setup(resolved.connection_ctx)
    resource_keys = []
    control = _control_instrument_selection(ctx)
    if isinstance(control, dict):
        endpoint = control.get("endpoint") if isinstance(control.get("endpoint"), dict) else {}
        config_path = control.get("config")
        if endpoint.get("host") and endpoint.get("port") is not None:
            resource_keys.append(f"probe:{endpoint.get('host')}:{endpoint.get('port')}")
        elif config_path:
            resource_keys.append(f"probe_path:{config_path}")
    if resolved.instrument_id and resolved.instrument_host and resolved.instrument_port is not None:
        resource_keys.append(f"instrument:{resolved.instrument_id}:{resolved.instrument_host}:{resolved.instrument_port}")
    payload = {
        "contract_version": 1,
        "controller": control,
        "control_instrument": control,
        "instrument": {
            "id": resolved.instrument_id,
            "communication": dict(resolved.instrument_communication or {}),
            "capability_surfaces": dict(resolved.instrument_capability_surfaces or {}),
        } if any([resolved.instrument_id, resolved.instrument_communication, resolved.instrument_capability_surfaces]) else None,
        "resource_keys": resource_keys,
        "resource_summary": summarize_resource_keys(resource_keys),
        "connection_setup": connection_setup,
    }
    payload["selection_digest"] = _bench_selection_digest(payload)
    return payload


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _abs(root: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def _load_instrument_instance_type(repo_root: Path, instrument_id: str | None) -> str | None:
    instance_id = str(instrument_id or "").strip()
    if not instance_id:
        return None
    path = repo_root / "configs" / "instrument_instances" / f"{instance_id}.yaml"
    if not path.exists():
        return None
    raw = _simple_yaml_load(str(path))
    instance = raw.get("instance", {}) if isinstance(raw, dict) else {}
    if not isinstance(instance, dict):
        return None
    type_id = str(instance.get("type") or raw.get("type") or "").strip()
    return type_id or None


def _load_context(board_id: str, test_path: str, repo_root: Path) -> Dict[str, Any]:
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    test_file = _abs(repo_root, test_path)
    if not test_file.exists():
        raise FileNotFoundError(f"test not found: {test_file}")
    test_raw = _load_json(test_file)
    board_exists = board_path.exists()
    ownership_kind = "board_owned"
    if not board_exists:
        if isinstance(test_raw.get("instrument"), dict) and test_raw.get("selftest"):
            ownership_kind = "instrument_owned"
        else:
            raise FileNotFoundError(f"board config not found: {board_path}")
    override_instance_id, override_probe_rel = resolve_control_instrument_override(repo_root, test_raw)
    probe_rel = None
    instance_id = None
    if ownership_kind == "board_owned":
        probe_rel = override_probe_rel or resolve_control_instrument_config(str(repo_root), args=None, board_id=board_id)
        instance_id = override_instance_id or resolve_control_instrument_instance(str(repo_root), args=None, board_id=board_id)
    else:
        probe_rel = override_probe_rel
        instance_id = override_instance_id
    if probe_rel or instance_id:
        binding = load_probe_binding(
            repo_root,
            probe_path=None if instance_id else probe_rel,
            instance_id=instance_id,
        )
        probe_path = Path(str(binding.config_path))
        probe_path_rel = probe_path.relative_to(repo_root).as_posix()
    else:
        binding = empty_probe_binding()
        probe_path_rel = None
    board_raw = _simple_yaml_load(str(board_path)) if board_exists else {"board": {"name": board_id, "target": board_id}}
    probe_raw = binding.raw
    resolved = resolve_run_strategy(probe_raw, board_raw, test_raw, wiring=None, request_timeout_s=None, repo_root=repo_root)
    return {
        "ownership_kind": ownership_kind,
        "board_path": board_path.relative_to(repo_root).as_posix() if board_exists else None,
        "test_path": test_file.relative_to(repo_root).as_posix(),
        "probe_path": probe_path_rel,
        "probe_instance_id": binding.instance_id,
        "probe_type": binding.type_id,
        "probe_communication": binding.communication,
        "probe_capability_surfaces": binding.capability_surfaces,
        "board_raw": board_raw,
        "test_raw": test_raw,
        "probe_raw": probe_raw,
        "resolved": resolved,
    }


def _plan_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx["resolved"]
    board_cfg = resolved.board_cfg
    test_raw = ctx["test_raw"]
    metadata = extract_plan_metadata(test_raw)
    explanation = _metadata_explanation(metadata)
    selected_instrument_id = ctx.get("probe_instance_id") or resolved.instrument_id
    selected_instrument_type = ctx.get("probe_type")
    if not selected_instrument_type and resolved.instrument_id:
        selected_instrument_type = _load_instrument_instance_type(REPO_ROOT, resolved.instrument_id) or (InstrumentRegistry().get(resolved.instrument_id) or {}).get("type")
    supported_instrument_advisory = _supported_instrument_advisory(
        metadata.get("supported_instruments"),
        selected_instrument_id=selected_instrument_id,
        selected_instrument_type=selected_instrument_type,
    )
    build_kind, known_firmware_path, _build_step = resolve_build_stage(
        board_cfg=board_cfg,
        verify_only=False,
        no_build=False,
        repo_root=REPO_ROOT,
        output_mode="quiet",
        build_log_path="<build_log>",
    )
    _load_step, flash_cfg = resolve_load_stage(
        board_cfg=board_cfg,
        wiring_cfg=resolved.wiring_cfg,
        probe_cfg=resolved.probe_cfg,
        known_firmware_path=known_firmware_path,
        verify_only=False,
        skip_flash=False,
        repo_root=REPO_ROOT,
        output_mode="quiet",
        flash_json_path="<flash_json>",
        flash_log_path="<flash_log>",
    )
    check_model = "instrument_signature" if isinstance(test_raw.get("instrument"), dict) else "signal_verify"
    capability_surface_plan: List[Dict[str, Any]] = []
    probe_surfaces = ctx.get("probe_capability_surfaces") or {}
    probe_comm = ctx.get("probe_communication") or {}
    if flash_cfg.get("method") in ("gdbmi", "flash_bmda_gdbmi", "bmda_gdbmi") or ctx.get("probe_instance_id"):
        capability_surface_plan.append(
            {
                "owner": "probe",
                "capability": "swd",
                "surface": resolve_capability_surface("swd", probe_surfaces, probe_comm),
                "reason": "flash/debug path",
            }
        )
    if check_model == "signal_verify":
        capability_surface_plan.append(
            {
                "owner": "probe",
                "capability": "gpio_in",
                "surface": resolve_capability_surface("gpio_in", probe_surfaces, probe_comm),
                "reason": "signal verification capture",
            }
        )
    if check_model == "instrument_signature":
        inst_comm = resolved.instrument_communication
        inst_surfaces = resolved.instrument_capability_surfaces
        bench_setup = test_raw.get("bench_setup", {}) if isinstance(test_raw.get("bench_setup"), dict) else {}
        if isinstance(bench_setup.get("dut_to_instrument"), list) and bench_setup.get("dut_to_instrument"):
            capability_surface_plan.append(
                {
                    "owner": "instrument",
                    "capability": "measure.digital",
                    "surface": resolve_capability_surface("measure.digital", inst_surfaces, inst_comm),
                    "reason": "digital signature verification",
                }
            )
        if isinstance(bench_setup.get("dut_to_instrument_analog"), list) and bench_setup.get("dut_to_instrument_analog"):
            capability_surface_plan.append(
                {
                    "owner": "instrument",
                    "capability": "measure.voltage",
                    "surface": resolve_capability_surface("measure.voltage", inst_surfaces, inst_comm),
                    "reason": "analog verification",
                }
            )
    return {
        "ok": True,
        "stage": "plan",
        "board": board_id,
        "test": {"name": test_raw.get("name"), "path": ctx["test_path"]},
        "selected": {
            "selected_dut": _selected_dut_payload(board_id, ctx),
            "selected_board_profile": _selected_board_profile_payload(board_id, ctx),
            "selected_bench_resources": _selected_bench_resources_payload(ctx),
            "ownership_kind": ctx.get("ownership_kind"),
            "plan_schema_kind": "structured" if metadata.get("schema_version") != "legacy" else "legacy",
            "schema_version": metadata.get("schema_version"),
            "test_kind": metadata.get("test_kind"),
            "supported_instruments": metadata.get("supported_instruments"),
            "requires": metadata.get("requires"),
            "labels": metadata.get("labels"),
            "covers": metadata.get("covers"),
            "verification_mode_summary": explanation.get("verification_mode_summary"),
            "requires_summary": explanation.get("requires_summary"),
            "supported_instrument_advisory": supported_instrument_advisory,
            "test_validation_errors": list(metadata.get("validation_errors") or []),
            "controller_selection": _control_instrument_selection(ctx),
            "control_instrument_selection": _control_instrument_selection(ctx),
            "controller": ctx["probe_path"],
            "control_instrument": ctx["probe_path"],
            "controller_instance": ctx.get("probe_instance_id"),
            "control_instrument_instance": ctx.get("probe_instance_id"),
            "controller_type": ctx.get("probe_type"),
            "control_instrument_type": ctx.get("probe_type"),
            "controller_communication": ctx.get("probe_communication"),
            "control_instrument_communication": ctx.get("probe_communication"),
            "controller_capability_surfaces": ctx.get("probe_capability_surfaces"),
            "control_instrument_capability_surfaces": ctx.get("probe_capability_surfaces"),
            "instrument_communication": resolved.instrument_communication,
            "instrument_capability_surfaces": resolved.instrument_capability_surfaces,
            "builder_kind": build_kind,
            "firmware_project": (board_cfg.get("build") or {}).get("project_dir"),
            "board_clock_hz": board_cfg.get("clock_hz"),
            "flash_method": flash_cfg.get("method") if isinstance(flash_cfg, dict) else None,
            "wiring": resolved.wiring_cfg,
            "verification_views": dict(resolved.connection_ctx.verification_views),
            "connection_setup": build_connection_setup(resolved.connection_ctx),
            "check_model": check_model,
            "capability_surface_plan": capability_surface_plan,
            "compatibility": {
                "probe": ctx["probe_path"],
                "probe_instance": ctx.get("probe_instance_id"),
                "probe_type": ctx.get("probe_type"),
                "probe_communication": ctx.get("probe_communication"),
                "probe_capability_surfaces": ctx.get("probe_capability_surfaces"),
            },
        },
        "includes": [
            "board and test selection",
            "probe selection when required",
            "builder and flash strategy resolution",
            "wiring assumptions",
            "check model selection",
            "structured test metadata when present",
        ],
        "does_not_confirm": [
            "probe reachability",
            "DUT presence",
            "flash success",
            "signal correctness on real hardware",
        ],
    }


def _preflight_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx["resolved"]
    schema_advisories = _resolved_schema_advisories(ctx)
    step = build_preflight_step(ctx["test_raw"], normalize_probe_cfg(ctx["probe_raw"]), out_json="<preflight_json>", output_mode="quiet", log_path="<preflight_log>")
    enabled = step is not None
    checks: List[str] = []
    confirms: List[str] = []
    does_not_confirm: List[str] = []
    if enabled:
        checks = [
            "probe host reachability",
            "probe TCP connectivity",
            "monitor/target discovery",
            "logic-analyzer self-test",
            "probe-side port/config sanity",
        ]
        confirms = [
            "ESP32JTAG probe is reachable",
            "probe backend is alive",
            "logic-analyzer path is available",
        ]
        does_not_confirm = [
            "DUT SWD wiring correctness",
            "flash success on the DUT",
            "DUT firmware behavior",
            "signal correctness on the DUT pin",
        ]
    return {
        "ok": True,
        "stage": "pre-flight",
        "board": board_id,
        "test": {"name": ctx["test_raw"].get("name"), "path": ctx["test_path"]},
        "enabled": enabled,
        "probe": ctx["probe_path"],
        "checks": checks,
        "confirms": confirms,
        "does_not_confirm": does_not_confirm,
        "schema_advisories": schema_advisories,
        "reason_if_skipped": "pre-flight disabled by configuration" if not enabled else None,
        "wiring_assumptions": resolved.wiring_cfg,
        "connection_setup": build_connection_setup(resolved.connection_ctx),
    }


def _run_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    board_cfg = ctx["resolved"].board_cfg
    build_kind, _, _ = resolve_build_stage(board_cfg=board_cfg, verify_only=False, no_build=False, repo_root=REPO_ROOT, output_mode="quiet", build_log_path="<build_log>")
    flash_cfg = (board_cfg.get("flash") or {}) if isinstance(board_cfg.get("flash"), dict) else {}
    return {
        "ok": True,
        "stage": "run",
        "board": board_id,
        "test": {"name": ctx["test_raw"].get("name"), "path": ctx["test_path"]},
        "includes": [
            f"build via {build_kind}",
            f"flash/load via {flash_cfg.get('method') or 'gdbmi'}",
            "runtime execution on DUT",
        ],
        "assumptions_in_effect": {
            "wiring": ctx["resolved"].wiring_cfg,
            "firmware_project": (board_cfg.get("build") or {}).get("project_dir"),
            "connection_setup": build_connection_setup(ctx["resolved"].connection_ctx),
        },
    }


def _check_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    verify_step = build_verify_step(
        test_raw=ctx["test_raw"],
        board_cfg=ctx["resolved"].board_cfg,
        probe_cfg=ctx["resolved"].probe_cfg,
        wiring_cfg=ctx["resolved"].wiring_cfg,
        artifacts_dir=REPO_ROOT / "artifacts" / "_describe_dummy",
        observe_log="<observe_log>",
        output_mode="quiet",
        measure_path="<measure_json>",
    )
    uart_step = build_uart_step(
        effective=ctx["test_raw"],
        board_cfg=ctx["resolved"].board_cfg,
        output_mode="quiet",
        observe_uart_log="<uart_raw>",
        uart_json="<uart_json>",
        flash_json="<flash_json>",
        observe_uart_step_log="<uart_step_log>",
    )
    checks: List[Dict[str, Any]] = []
    if uart_step:
        checks.append({
            "type": "uart",
            "expect_patterns": ((ctx["test_raw"].get("observe_uart") or {}).get("expect_patterns") if isinstance(ctx["test_raw"].get("observe_uart"), dict) else None),
        })
    if verify_step:
        checks.append({
            "type": verify_step.get("type"),
            "details": verify_step.get("inputs"),
        })
    return {
        "ok": True,
        "stage": "check",
        "board": board_id,
        "test": {"name": ctx["test_raw"].get("name"), "path": ctx["test_path"]},
        "checks": checks,
    }


def explain_stage(board_id: str, test_path: str, stage: str, repo_root: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    ctx = _load_context(board_id, test_path, root)
    normalized = str(stage).strip().lower()
    if normalized in ("plan",):
        return _plan_payload(board_id, ctx)
    if normalized in ("pre-flight", "preflight"):
        return _preflight_payload(board_id, ctx)
    if normalized in ("run",):
        return _run_payload(board_id, ctx)
    if normalized in ("check",):
        return _check_payload(board_id, ctx)
    return {"ok": False, "error": f"unsupported stage: {stage}"}


def render_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines = [f"stage: {payload.get('stage')}", f"board: {payload.get('board')}"]
    test = payload.get("test", {})
    lines.append(f"test: {test.get('name')} ({test.get('path')})")
    if payload.get("selected"):
        lines.append("selected:")
        selected = payload.get("selected") or {}
        has_control_selection = isinstance(selected.get("controller_selection") or selected.get("control_instrument_selection"), dict) and bool(
            selected.get("controller_selection") or selected.get("control_instrument_selection")
        )
        for k, v in (payload.get("selected") or {}).items():
            if has_control_selection and k in (
                "probe",
                "probe_instance",
                "probe_type",
                "probe_communication",
                "probe_capability_surfaces",
            ):
                continue
            if k in (
                "controller_communication",
                "control_instrument_communication",
                "instrument_communication",
                "controller_capability_surfaces",
                "control_instrument_capability_surfaces",
                "instrument_capability_surfaces",
                "probe_communication",
                "probe_capability_surfaces",
            ) and isinstance(v, dict):
                lines.append(f"  - {k}:")
                for inner_k, inner_v in v.items():
                    lines.append(f"    {inner_k}: {inner_v}")
                continue
            if k == "capability_surface_plan" and isinstance(v, list):
                lines.append(f"  - {k}:")
                for item in v:
                    lines.append(f"    {json.dumps(item, sort_keys=True)}")
                continue
            if k in ("controller_selection", "control_instrument_selection") and isinstance(v, dict):
                lines.append(f"  - {k}:")
                for inner_k, inner_v in v.items():
                    lines.append(f"    {inner_k}: {inner_v}")
                continue
            if k == "test_validation_errors" and isinstance(v, list):
                lines.append(f"  - {k}:")
                for item in v:
                    lines.append(f"    - {item}")
                continue
            if k in ("selected_dut", "selected_board_profile", "selected_bench_resources") and isinstance(v, dict):
                lines.append(f"  - {k}:")
                for inner_k, inner_v in v.items():
                    if inner_k == "connection_setup" and isinstance(inner_v, dict):
                        lines.append(f"    {inner_k}:")
                        lines.extend(render_connection_setup_text(inner_v, indent="      "))
                        continue
                    lines.append(f"    {inner_k}: {inner_v}")
                continue
            if k == "connection_setup" and isinstance(v, dict):
                lines.append(f"  - {k}:")
                lines.extend(render_connection_setup_text(v, indent="    "))
                continue
            if k in ("supported_instruments", "labels", "covers") and isinstance(v, list):
                lines.append(f"  - {k}: {', '.join(str(item) for item in v)}")
                continue
            lines.append(f"  - {k}: {v}")
    if payload.get("checks") is not None:
        lines.append("checks:")
        for item in payload.get("checks") or []:
            lines.append(f"  - {json.dumps(item, sort_keys=True)}")
    if payload.get("schema_advisories"):
        lines.append("schema_advisories:")
        for item in payload.get("schema_advisories") or []:
            lines.append(f"  - {item}")
    if payload.get("includes"):
        lines.append("includes:")
        for item in payload.get("includes") or []:
            lines.append(f"  - {item}")
    if payload.get("confirms"):
        lines.append("confirms:")
        for item in payload.get("confirms") or []:
            lines.append(f"  - {item}")
    if payload.get("does_not_confirm"):
        lines.append("does_not_confirm:")
        for item in payload.get("does_not_confirm") or []:
            lines.append(f"  - {item}")
    if payload.get("reason_if_skipped"):
        lines.append(f"reason_if_skipped: {payload.get('reason_if_skipped')}")
    if payload.get("assumptions_in_effect"):
        lines.append("assumptions_in_effect:")
        for k, v in (payload.get("assumptions_in_effect") or {}).items():
            if k == "connection_setup" and isinstance(v, dict):
                lines.append(f"  - {k}:")
                lines.extend(render_connection_setup_text(v, indent="    "))
                continue
            lines.append(f"  - {k}: {v}")
    if payload.get("connection_setup"):
        lines.append("connection_setup:")
        lines.extend(render_connection_setup_text(payload.get("connection_setup"), indent="  "))
    if payload.get("wiring_assumptions"):
        lines.append(f"wiring_assumptions: {payload.get('wiring_assumptions')}")
    return "\n".join(lines).rstrip() + "\n"
