"""Centralized CLI policy resolver for probe/board/tool defaults.

This module is the single place where board/probe default policies live.
The CLI should call into these helpers instead of embedding policy directly.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Optional


_DEFAULTS: Dict[str, str] = {
    "probe_config": os.path.join("configs", "esp32jtag.yaml"),
    "notify_probe_config": os.path.join("configs", "esp32jtag_notify.yaml"),
    "doctor_board_config": os.path.join("configs", "boards", "rp2040_pico.yaml"),
}

_NOTIFY_BOARDS = {"esp32s3_devkit"}
_DOCTOR_REQUIRED_TOOLS = ("arm-none-eabi-gdb", "arm-none-eabi-gcc", "cmake")


def _arg(args: Any, name: str, default: Any = None) -> Any:
    if args is None:
        return default
    return getattr(args, name, default)


def _board_for_policy(board_id: Optional[str], args: Any, pack_meta: Optional[dict]) -> Optional[str]:
    if board_id:
        return board_id
    if isinstance(pack_meta, dict):
        board = pack_meta.get("board")
        if board:
            return str(board)
    arg_board = _arg(args, "board")
    return str(arg_board) if arg_board else None


def _use_absolute_paths(repo_root: str, pack_meta: Optional[dict]) -> bool:
    if not isinstance(pack_meta, dict):
        return False
    mode = str(pack_meta.get("mode", "")).lower()
    if mode == "pack":
        return True
    if bool(pack_meta.get("absolute_paths")):
        return True
    return False


def _normalize_path(repo_root: str, path: str, absolute: bool) -> str:
    if not path:
        return path
    if absolute and not os.path.isabs(path):
        return os.path.join(repo_root, path)
    return path


def resolve_notify_probe_config(
    repo_root: str,
    args: Any,
    board_id: Optional[str] = None,
    pack_meta: Optional[dict] = None,
) -> Optional[str]:
    """Return notify-probe config path when policy says it should be used."""
    user_notify = _arg(args, "notify_probe")
    if user_notify:
        return str(user_notify)

    explicit_probe = _arg(args, "probe")
    if explicit_probe:
        return None

    policy_board = _board_for_policy(board_id, args, pack_meta)
    dut_id = _arg(args, "dut")
    if policy_board not in _NOTIFY_BOARDS and dut_id not in _NOTIFY_BOARDS:
        return None

    notify_rel = _DEFAULTS["notify_probe_config"]
    notify_abs = os.path.join(repo_root, notify_rel)
    if not os.path.exists(notify_abs):
        return None

    absolute = _use_absolute_paths(repo_root, pack_meta)
    return _normalize_path(repo_root, notify_rel, absolute)


def resolve_probe_config(
    repo_root: str,
    args: Any,
    board_id: Optional[str] = None,
    pack_meta: Optional[dict] = None,
) -> str:
    """Resolve probe config path with user override + policy defaults."""
    user_probe = _arg(args, "probe")
    if user_probe:
        return str(user_probe)

    notify = resolve_notify_probe_config(repo_root, args, board_id=board_id, pack_meta=pack_meta)
    if notify:
        return notify

    absolute = _use_absolute_paths(repo_root, pack_meta)
    return _normalize_path(repo_root, _DEFAULTS["probe_config"], absolute)


def resolve_board_config(repo_root: str, args: Any, pack_meta: Optional[dict] = None) -> Optional[str]:
    """Resolve board config path with user override + command defaults."""
    user_board = _arg(args, "board")
    if user_board:
        return str(user_board)

    if isinstance(pack_meta, dict):
        pack_board = pack_meta.get("board")
        if pack_board:
            return str(pack_board)

    cmd = str(_arg(args, "cmd", "")).lower()
    if cmd == "doctor":
        return _DEFAULTS["doctor_board_config"]
    return None


def resolve_doctor_required_tools(_args: Any = None) -> Iterable[str]:
    """Tool list for doctor checks (kept policy-driven, not in CLI code)."""
    return _DOCTOR_REQUIRED_TOOLS
