from __future__ import annotations

from pathlib import Path
from typing import Dict, Any


def default_firmware_path(repo_root: Path, board_cfg: Dict[str, Any], build_kind: str) -> str:
    # Adapter-layer artifact naming hints used by no-build fallback mode.
    if build_kind == "arm_debug":
        return str(repo_root / "artifacts" / "build_stm32" / "stm32f103_app.elf")
    if build_kind == "idf":
        target = str(board_cfg.get("target") or "esp32s3").strip()
        return str(repo_root / "artifacts" / f"build_{target}" / "ael_esp32s3.elf")
    return str(repo_root / "artifacts" / "build" / "pico_blink.elf")
