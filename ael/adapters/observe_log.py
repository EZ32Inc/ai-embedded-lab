from __future__ import annotations

from typing import Any, Dict

from ael.adapters import observe_uart_log


def run_serial_log(cfg: Dict[str, Any], raw_log_path: str) -> Dict[str, Any]:
    # Role-first facade: serial transport remains an internal backend detail.
    return observe_uart_log.run(cfg, raw_log_path=raw_log_path)


def run(cfg: Dict[str, Any], raw_log_path: str) -> Dict[str, Any]:
    # Compatibility alias for callers expecting a generic observe_log entrypoint.
    return run_serial_log(cfg, raw_log_path=raw_log_path)
