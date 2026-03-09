from __future__ import annotations

import json
import os
import subprocess
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
        stop_on_fail = bool(setting.get("stop_on_fail", True))
        if not isinstance(steps, list) or not steps:
            return 2, {"ok": False, "mode": mode, "error": "sequence mode requires non-empty steps"}
        overall_ok = True
        last_code = 0
        for idx, raw_step in enumerate(steps, start=1):
            step = dict(raw_step) if isinstance(raw_step, dict) else {}
            step_name = str(step.get("name") or f"step_{idx:02d}")
            action = str(step.get("action") or "single_run").strip().lower()
            if action == "preflight_only":
                if not step.get("probe") and setting.get("probe"):
                    step["probe"] = setting.get("probe")
                if not step.get("instrument_instance") and setting.get("instrument_instance"):
                    step["instrument_instance"] = setting.get("instrument_instance")
                code, result = _run_preflight_only(repo_root, step)
            else:
                # default action is run test step
                if not step.get("probe") and setting.get("probe"):
                    step["probe"] = setting.get("probe")
                if not step.get("instrument_instance") and setting.get("instrument_instance"):
                    step["instrument_instance"] = setting.get("instrument_instance")
                code, result = _run_single(repo_root, step, output_mode)
            ok = code == 0
            results.append({"name": step_name, "code": code, "ok": ok, "result": result})
            if not ok:
                overall_ok = False
                last_code = code
                if stop_on_fail:
                    break
        return (0 if overall_ok else last_code or 1), {"ok": overall_ok, "mode": mode, "results": results}

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
