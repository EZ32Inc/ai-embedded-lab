from __future__ import annotations

from pathlib import Path
from typing import Any

from ael.adapters import observe_gpio_pin
from ael.config_resolver import resolve_controller_config, resolve_controller_instance
from ael.pipeline import _normalize_probe_cfg, _simple_yaml_load
from ael.probe_binding import load_probe_binding


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_probe_cfg(*, board: str | None = None, probe: str | None = None) -> tuple[str, dict[str, Any]]:
    repo_root = str(_repo_root())
    instance_id = resolve_controller_instance(repo_root, args=None, board_id=board)
    probe_path = str(probe or resolve_controller_config(repo_root, args=None, board_id=board))
    binding = load_probe_binding(
        repo_root,
        probe_path=None if instance_id and not probe else probe_path,
        instance_id=instance_id if instance_id and not probe else None,
    )
    probe_cfg = _normalize_probe_cfg(binding.raw)
    return str(binding.config_path), probe_cfg


def run(
    *,
    pin: str,
    board: str | None = None,
    probe: str | None = None,
    duration_s: float = 1.0,
    expected_hz: float = 1.0,
    min_edges: int = 1,
) -> dict[str, Any]:
    probe_path, probe_cfg = resolve_probe_cfg(board=board, probe=probe)
    capture: dict[str, Any] = {}
    observed = observe_gpio_pin.run(
        probe_cfg,
        pin=pin,
        duration_s=float(duration_s),
        expected_hz=float(expected_hz),
        min_edges=max(1, int(min_edges)),
        max_edges=200000,
        capture_out=capture,
        verify_edges=False,
    )
    edges = int(capture.get("edges", 0) or 0)
    return {
        "ok": bool(observed),
        "toggling": bool(observed and edges >= max(1, int(min_edges))),
        "pin": str(pin),
        "controller": {
            "config": probe_path,
            "name": str(probe_cfg.get("name") or ""),
            "host": str(probe_cfg.get("ip") or ""),
        },
        "control_instrument": {
            "config": probe_path,
            "name": str(probe_cfg.get("name") or ""),
            "host": str(probe_cfg.get("ip") or ""),
        },
        "controller_config": probe_path,
        "control_instrument_config": probe_path,
        "controller_name": str(probe_cfg.get("name") or ""),
        "control_instrument_name": str(probe_cfg.get("name") or ""),
        "controller_host": str(probe_cfg.get("ip") or ""),
        "control_instrument_host": str(probe_cfg.get("ip") or ""),
        "probe_path": probe_path,
        "probe_name": str(probe_cfg.get("name") or ""),
        "probe_host": str(probe_cfg.get("ip") or ""),
        "duration_s": float(duration_s),
        "sample_rate_hz": int(capture.get("sample_rate_hz", 0) or 0),
        "window_s": float(capture.get("window_s", 0.0) or 0.0),
        "edges": edges,
        "high": int(capture.get("high", 0) or 0),
        "low": int(capture.get("low", 0) or 0),
        "min_edges": max(1, int(min_edges)),
    }
