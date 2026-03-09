from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ael.pipeline import _simple_yaml_load
from ael.strategy_resolver import (
    build_preflight_step,
    build_uart_step,
    build_verify_step,
    normalize_probe_cfg,
    resolve_build_stage,
    resolve_load_stage,
    resolve_run_strategy,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE = "configs/esp32jtag.yaml"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _abs(root: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def _load_context(board_id: str, test_path: str, repo_root: Path) -> Dict[str, Any]:
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not board_path.exists():
        raise FileNotFoundError(f"board config not found: {board_path}")
    test_file = _abs(repo_root, test_path)
    if not test_file.exists():
        raise FileNotFoundError(f"test not found: {test_file}")
    probe_path = repo_root / DEFAULT_PROBE
    board_raw = _simple_yaml_load(str(board_path))
    test_raw = _load_json(test_file)
    probe_raw = _simple_yaml_load(str(probe_path))
    resolved = resolve_run_strategy(probe_raw, board_raw, test_raw, wiring=None, request_timeout_s=None, repo_root=repo_root)
    return {
        "board_path": board_path.relative_to(repo_root).as_posix(),
        "test_path": test_file.relative_to(repo_root).as_posix(),
        "probe_path": probe_path.relative_to(repo_root).as_posix(),
        "board_raw": board_raw,
        "test_raw": test_raw,
        "probe_raw": probe_raw,
        "resolved": resolved,
    }


def _plan_payload(board_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    resolved = ctx["resolved"]
    board_cfg = resolved.board_cfg
    test_raw = ctx["test_raw"]
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
    return {
        "ok": True,
        "stage": "plan",
        "board": board_id,
        "test": {"name": test_raw.get("name"), "path": ctx["test_path"]},
        "selected": {
            "probe": ctx["probe_path"],
            "builder_kind": build_kind,
            "firmware_project": (board_cfg.get("build") or {}).get("project_dir"),
            "board_clock_hz": board_cfg.get("clock_hz"),
            "flash_method": flash_cfg.get("method") if isinstance(flash_cfg, dict) else None,
            "wiring": resolved.wiring_cfg,
            "verification_views": (board_cfg.get("verification_views", {}) if isinstance(board_cfg.get("verification_views"), dict) else {}),
            "check_model": check_model,
        },
        "includes": [
            "board and test selection",
            "probe selection",
            "builder and flash strategy resolution",
            "wiring assumptions",
            "check model selection",
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
        "reason_if_skipped": "pre-flight disabled by configuration" if not enabled else None,
        "wiring_assumptions": resolved.wiring_cfg,
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
        for k, v in (payload.get("selected") or {}).items():
            lines.append(f"  - {k}: {v}")
    if payload.get("checks") is not None:
        lines.append("checks:")
        for item in payload.get("checks") or []:
            lines.append(f"  - {json.dumps(item, sort_keys=True)}")
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
            lines.append(f"  - {k}: {v}")
    if payload.get("wiring_assumptions"):
        lines.append(f"wiring_assumptions: {payload.get('wiring_assumptions')}")
    return "\n".join(lines).rstrip() + "\n"
