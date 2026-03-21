"""
DUT loader: converts a raw board YAML dict into a DUTConfig.

Supports both the legacy format (flat `target:` field) and the new format
(structured `processors:[]` list). The compat path auto-promotes legacy
configs so callers never need to handle both shapes.
"""

from __future__ import annotations

from typing import Any, Dict

from ael.dut.model import DUTConfig, ProcessorConfig

# Mapping from known target IDs to CPU architecture.
# Extend as new board targets are added.
_TARGET_ARCH_MAP: Dict[str, str] = {
    "esp32c3": "riscv",
    "esp32c6": "riscv",
    "esp32s3": "xtensa",
    "esp32":   "xtensa",
    "rp2040":  "arm",
    "rp2350":  "arm",
    # STM32 families
    "stm32f1": "arm",
    "stm32f4": "arm",
    "stm32g4": "arm",
    "stm32h7": "arm",
}


def _infer_arch(target: str) -> str:
    if target in _TARGET_ARCH_MAP:
        return _TARGET_ARCH_MAP[target]
    # STM32 parts all start with "stm32"
    if target.lower().startswith("stm32"):
        return "arm"
    return "unknown"


def load_dut(board_id: str, raw: Dict[str, Any]) -> DUTConfig:
    """
    Parse a raw board YAML dict (the value under the top-level `board:` key)
    into a DUTConfig.

    Supports two input shapes:

    Legacy (existing boards):
        target: esp32c3
        name: ESP32-C3 DevKit

    New (after Step 3 YAML update):
        target: esp32c3   # kept for toolchain compat
        processors:
          - id: esp32c3
            arch: riscv
            role: primary
            clock_hz: 160000000
    """
    if not isinstance(raw, dict):
        raw = {}

    name = str(raw.get("name") or board_id)

    # Parse processors — new format takes priority
    raw_procs = raw.get("processors")
    if isinstance(raw_procs, list) and raw_procs:
        processors = []
        for i, p in enumerate(raw_procs):
            if not isinstance(p, dict):
                continue
            proc_id = str(p.get("id") or p.get("target") or "unknown")
            arch = str(p.get("arch") or _infer_arch(proc_id))
            role = str(p.get("role") or ("primary" if i == 0 else "secondary"))
            clock_hz = p.get("clock_hz")
            extra = {k: v for k, v in p.items()
                     if k not in ("id", "target", "arch", "role", "clock_hz")}
            processors.append(ProcessorConfig(
                id=proc_id, arch=arch, role=role,
                clock_hz=int(clock_hz) if clock_hz is not None else None,
                extra=extra,
            ))
    else:
        # Legacy: promote flat `target:` to a single-processor list
        target = str(raw.get("target") or board_id)
        arch = _infer_arch(target)
        clock_hz = raw.get("clock_hz")
        processors = [ProcessorConfig(
            id=target, arch=arch, role="primary",
            clock_hz=int(clock_hz) if clock_hz is not None else None,
        )]

    known_keys = {
        "name", "target", "processors", "build", "flash",
        "observe_map", "observe", "pins", "capabilities",
        "instrument", "clock_hz",
    }
    extra = {k: v for k, v in raw.items() if k not in known_keys}

    return DUTConfig(
        board_id=board_id,
        name=name,
        processors=processors,
        build=dict(raw.get("build") or {}),
        flash=dict(raw.get("flash") or {}),
        observe_map=dict(raw.get("observe_map") or {}),
        observe=dict(raw.get("observe") or {}),
        pins=dict(raw.get("pins") or {}),
        capabilities=dict(raw.get("capabilities") or {}),
        instrument=dict(raw.get("instrument") or {}),
        extra=extra,
    )
