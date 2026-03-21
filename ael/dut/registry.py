"""
DUT registry: loads a DUTConfig from the configs/boards/ directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ael.dut.loader import load_dut
from ael.dut.model import DUTConfig


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback minimal YAML parser (mirrors pipeline.py _simple_yaml_load)
        data: Dict[str, Any] = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                key, _, value = line.strip().partition(":")
                if value.strip():
                    data[key.strip()] = value.strip().strip('"')
        return data


def load_dut_from_file(repo_root: Path, board_id: str) -> DUTConfig:
    """
    Load a DUTConfig from configs/boards/{board_id}.yaml.

    Args:
        repo_root: Repository root directory.
        board_id:  Board identifier, e.g. "esp32c3_devkit".

    Returns:
        DUTConfig parsed from the board YAML file.

    Raises:
        FileNotFoundError: If the board config file does not exist.
    """
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not board_path.exists():
        raise FileNotFoundError(
            f"Board config not found: {board_path}. "
            f"Expected at configs/boards/{board_id}.yaml"
        )
    raw_top = _load_yaml(board_path)
    # Board configs have a top-level `board:` key
    raw_board = raw_top.get("board") if isinstance(raw_top, dict) else raw_top
    if not isinstance(raw_board, dict):
        raw_board = {}
    return load_dut(board_id, raw_board)
