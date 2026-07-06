from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GoldenReference:
    target_family: str
    instrument_family: str
    board: str
    pack: str
    skill_doc: str
    source_run: str
    reason: str
    exact: bool = True


_REFERENCES: tuple[GoldenReference, ...] = (
    GoldenReference(
        target_family="rp2040",
        instrument_family="esp32jtag",
        board="rp2040_pico_s3jtag",
        pack="rp2040_s3jtag_full",
        skill_doc="docs/skills/rp2040_s3jtag_standard_suite_skill_2026-03-26.md",
        source_run="pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag",
        reason="validated RP2040 S3JTAG full suite; reuse its board flash config before trying manual GDB commands",
    ),
    GoldenReference(
        target_family="stm32f103",
        instrument_family="esp32jtag",
        board="stm32f103c6t6_bluepill_like",
        pack="stm32f103c6t6_golden",
        skill_doc="docs/skills/stm32f103c6t6_esp32jtag_golden_suite_skill_2026-04-01.md",
        source_run="pack_runs/2026-04-01_11-11-47_stm32f103c6t6_golden_stm32f103c6t6_bluepill_like",
        reason="validated STM32F103C6T6 ESP32JTAG golden suite; reuse its staged board config and flash flow",
    ),
)

_CLOSEST_FAMILY: dict[tuple[str, str], GoldenReference] = {
    ("rp2350", "esp32jtag"): GoldenReference(
        target_family="rp2350",
        instrument_family="esp32jtag",
        board="rp2040_pico_s3jtag",
        pack="rp2040_s3jtag_full",
        skill_doc="docs/skills/rp2040_s3jtag_standard_suite_skill_2026-03-26.md",
        source_run="pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag",
        reason="no exact RP2350 golden reference is registered; RP2040 is the closest successful RP-family ESP32JTAG reference",
        exact=False,
    ),
    ("rp2354", "esp32jtag"): GoldenReference(
        target_family="rp2354",
        instrument_family="esp32jtag",
        board="rp2040_pico_s3jtag",
        pack="rp2040_s3jtag_full",
        skill_doc="docs/skills/rp2040_s3jtag_standard_suite_skill_2026-03-26.md",
        source_run="pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag",
        reason="no exact RP2354 golden reference is registered; RP2040 is the closest successful RP-family ESP32JTAG reference",
        exact=False,
    ),
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def target_family(target: str) -> str:
    value = _norm(target)
    if value.startswith("stm32f103"):
        return "stm32f103"
    if value.startswith("rp2040"):
        return "rp2040"
    if value.startswith("rp2354"):
        return "rp2354"
    if value.startswith("rp2350"):
        return "rp2350"
    return value


def instrument_family(instrument: str) -> str:
    value = _norm(instrument)
    if any(token in value for token in ("coreweaver", "esp32jtag", "s3jtag", "esp32_jtag")):
        return "esp32jtag"
    if "stlink" in value or "st_link" in value:
        return "stlink"
    if "daplink" in value or "cmsis_dap" in value:
        return "daplink"
    return value


def resolve(target: str, instrument: str, *, allow_closest: bool = True) -> dict[str, Any]:
    tf = target_family(target)
    inf = instrument_family(instrument)
    for ref in _REFERENCES:
        if ref.target_family == tf and ref.instrument_family == inf:
            return _payload(ref, requested_target=target, requested_instrument=instrument)
    if allow_closest:
        ref = _CLOSEST_FAMILY.get((tf, inf))
        if ref:
            return _payload(ref, requested_target=target, requested_instrument=instrument)
    return {
        "ok": False,
        "requested_target": target,
        "requested_instrument": instrument,
        "target_family": tf,
        "instrument_family": inf,
        "error": "no golden reference found",
        "next_step": "create or identify a successful closest example before hand-building a flash sequence",
    }


def _payload(ref: GoldenReference, *, requested_target: str, requested_instrument: str) -> dict[str, Any]:
    board_config = f"configs/boards/{ref.board}.yaml"
    pack_path = f"packs/{ref.pack}.json"
    return {
        "ok": True,
        "exact": ref.exact,
        "requested_target": requested_target,
        "requested_instrument": requested_instrument,
        "target_family": ref.target_family,
        "instrument_family": ref.instrument_family,
        "board": ref.board,
        "board_config": board_config,
        "pack": ref.pack,
        "pack_path": pack_path,
        "skill_doc": ref.skill_doc,
        "source_run": ref.source_run,
        "reason": ref.reason,
        "rule": "reuse the referenced board flash config before composing manual GDB commands",
    }


def render_text(payload: dict[str, Any], *, repo_root: str | Path | None = None) -> str:
    lines: list[str] = []
    if not payload.get("ok"):
        lines.append("golden_reference_ok: false")
        lines.append(f"target_family: {payload.get('target_family', '')}")
        lines.append(f"instrument_family: {payload.get('instrument_family', '')}")
        lines.append(f"error: {payload.get('error', '')}")
        lines.append(f"next_step: {payload.get('next_step', '')}")
        return "\n".join(lines) + "\n"

    lines.append("golden_reference_ok: true")
    lines.append(f"exact: {str(bool(payload.get('exact'))).lower()}")
    lines.append(f"target_family: {payload.get('target_family', '')}")
    lines.append(f"instrument_family: {payload.get('instrument_family', '')}")
    lines.append(f"board: {payload.get('board', '')}")
    lines.append(f"board_config: {payload.get('board_config', '')}")
    lines.append(f"pack: {payload.get('pack', '')}")
    lines.append(f"pack_path: {payload.get('pack_path', '')}")
    lines.append(f"skill_doc: {payload.get('skill_doc', '')}")
    lines.append(f"source_run: {payload.get('source_run', '')}")
    lines.append(f"rule: {payload.get('rule', '')}")
    lines.append(f"reason: {payload.get('reason', '')}")
    if repo_root is not None:
        root = Path(repo_root)
        missing = [
            path
            for path in (
                payload.get("board_config"),
                payload.get("pack_path"),
                payload.get("skill_doc"),
                payload.get("source_run"),
            )
            if path and not (root / str(path)).exists()
        ]
        if missing:
            lines.append("missing_paths:")
            for path in missing:
                lines.append(f"  - {path}")
    return "\n".join(lines) + "\n"
