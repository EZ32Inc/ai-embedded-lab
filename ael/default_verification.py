from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ael import paths as ael_paths
from ael.adapters import preflight
from ael.pipeline import _normalize_probe_cfg, _simple_yaml_load, run_pipeline


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
            "probe": "configs/esp32jtag.yaml",
        }
    if key in ("rp2040_only", "rp2040_esp32jtag_only"):
        return {
            "version": 1,
            "mode": "single_run",
            "board": "rp2040_pico",
            "test": "tests/plans/gpio_signature.json",
            "probe": "configs/esp32jtag.yaml",
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
                    "probe": "configs/esp32jtag.yaml",
                },
                {
                    "name": "rp2040_golden_gpio_signature",
                    "board": "rp2040_pico",
                    "test": "tests/plans/gpio_signature.json",
                    "probe": "configs/esp32jtag.yaml",
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


def _run_preflight_only(repo_root: Path, probe_path: str | None) -> Tuple[int, Dict[str, Any]]:
    if not probe_path:
        print("default_verification: preflight_only missing probe path")
        return 2, {"ok": False, "error": "missing probe path"}
    probe_raw = _simple_yaml_load(probe_path)
    probe_cfg = _normalize_probe_cfg(probe_raw)
    ok, info = preflight.run(probe_cfg)
    return (0 if ok else 2), {"ok": bool(ok), "result": info or {}}


def _run_single(repo_root: Path, step: Dict[str, Any], output_mode: str) -> Tuple[int, Dict[str, Any]]:
    probe = _resolve_path(repo_root, step.get("probe"), "configs/esp32jtag.yaml")
    board = step.get("board")
    test = _resolve_path(repo_root, step.get("test"))
    if not board or not test:
        return 2, {"ok": False, "error": "single_run requires board and test"}
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
        probe = _resolve_path(repo_root, setting.get("probe"), "configs/esp32jtag.yaml")
        code, result = _run_preflight_only(repo_root, probe)
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
                probe = _resolve_path(repo_root, step.get("probe"), setting.get("probe") or "configs/esp32jtag.yaml")
                code, result = _run_preflight_only(repo_root, probe)
            else:
                # default action is run test step
                if not step.get("probe") and setting.get("probe"):
                    step["probe"] = setting.get("probe")
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
