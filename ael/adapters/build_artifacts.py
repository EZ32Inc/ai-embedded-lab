from __future__ import annotations

from pathlib import Path
from typing import Dict, Any


def default_firmware_path(repo_root: Path, board_cfg: Dict[str, Any], build_kind: str) -> str:
    # Adapter-layer artifact naming hints used by no-build fallback mode.
    if build_kind == "arm_debug":
        build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
        target = str(board_cfg.get("target") or "stm32").strip()
        artifact_stem = str(build_cfg.get("artifact_stem") or f"{target}_app").strip()
        return str(repo_root / "artifacts" / f"build_{target}" / f"{artifact_stem}.elf")
    if build_kind == "idf":
        target = str(board_cfg.get("target") or "esp32s3").strip()
        return str(repo_root / "artifacts" / f"build_{target}" / f"ael_{target}.elf")
    return str(repo_root / "artifacts" / "build" / "pico_blink.elf")
