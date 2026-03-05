from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _artifacts_dir(step: Dict[str, Any], ctx: Any) -> Path:
    inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
    run_dir = inputs.get("run_dir")
    if run_dir:
        return Path(run_dir) / "artifacts"
    if ctx is not None and getattr(ctx, "artifacts_dir", None):
        return Path(ctx.artifacts_dir)
    return Path("run") / "artifacts"


def _default_evidence_name(capability: str) -> str:
    mapping = {
        "measure.voltage": "instrument_voltage.json",
        "measure.digital": "instrument_digital.json",
        "uart_log": "uart_log.json",
    }
    return mapping.get(str(capability), "instrument_sim_response.json")


def _voltage_payload(instrument_id: str, params: Dict[str, Any], seed: int, noise_v: float) -> Dict[str, Any]:
    channel = str(params.get("channel", "ad0"))
    base_v = float(params.get("base_v", 3.2))
    rng = random.Random(seed + sum(ord(ch) for ch in channel))
    jitter = rng.uniform(-abs(noise_v), abs(noise_v))
    value_v = round(base_v + jitter, 4)
    return {
        "instrument_id": instrument_id,
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "capability": "measure.voltage",
        "channel": channel,
        "voltage_v": value_v,
        "ok": True,
    }


def _digital_signature_for_pin(pin: int) -> Dict[str, Any]:
    if pin == 4:
        return {"state": "toggle", "freq_hz": 1000.0, "duty": 0.5}
    if pin == 5:
        return {"state": "toggle", "freq_hz": 2000.0, "duty": 0.5}
    if pin == 6:
        return {"state": "high", "freq_hz": 0.0, "duty": 1.0}
    if pin == 7:
        return {"state": "low", "freq_hz": 0.0, "duty": 0.0}
    return {"state": "low", "freq_hz": 0.0, "duty": 0.0}


def _digital_payload(instrument_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    pins = params.get("pins", [4, 5, 6, 7])
    rows: List[Dict[str, Any]] = []
    for raw_pin in pins if isinstance(pins, list) else []:
        pin = int(raw_pin)
        sig = _digital_signature_for_pin(pin)
        rows.append(
            {
                "gpio": pin,
                "state": sig["state"],
                "freq_hz": sig["freq_hz"],
                "duty": sig["duty"],
            }
        )
    return {
        "instrument_id": instrument_id,
        "timestamp_utc": "2026-01-01T00:00:01Z",
        "capability": "measure.digital",
        "pins": rows,
        "ok": True,
    }


def _uart_payload(instrument_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    ready_count = int(params.get("ready_count", 3))
    lines = [
        "ESP-ROM:sim-boot",
        "I (10) main_task: Calling app_main()",
        "AEL_DUT_READY",
        "I (11) DUT: synthetic UART line",
    ]
    lines.extend(["AEL_DUT_READY"] * max(0, ready_count - 1))
    return {
        "instrument_id": instrument_id,
        "timestamp_utc": "2026-01-01T00:00:02Z",
        "capability": "uart_log",
        "lines": lines,
        "ok": True,
    }


def execute(step: Dict[str, Any], plan: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
    inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
    capability = str(inputs.get("capability", "")).strip()
    if not capability:
        return {"ok": False, "error_summary": "capability not set"}

    instrument_cfg = inputs.get("instrument", {}) if isinstance(inputs.get("instrument"), dict) else {}
    params = inputs.get("params", {}) if isinstance(inputs.get("params"), dict) else {}
    seed = int(instrument_cfg.get("seed", 12345))
    noise_v = float(instrument_cfg.get("noise_v", 0.002))
    instrument_id = str(instrument_cfg.get("id", "instrument_sim"))

    if capability == "measure.voltage":
        payload = _voltage_payload(instrument_id, params, seed, noise_v)
    elif capability == "measure.digital":
        payload = _digital_payload(instrument_id, params)
    elif capability == "uart_log":
        payload = _uart_payload(instrument_id, params)
    else:
        return {"ok": False, "error_summary": f"unsupported capability: {capability}"}

    artifacts_dir = _artifacts_dir(step, ctx)
    file_name = str(inputs.get("evidence_file", _default_evidence_name(capability)))
    out_path = artifacts_dir / file_name
    _write_json(out_path, payload)
    return {"ok": True, "result": payload, "artifacts": [str(out_path)]}
