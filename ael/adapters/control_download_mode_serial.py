from __future__ import annotations

from typing import Any, Dict

from ael.adapters import control_reset_serial


def assist_exit_download_mode(params: Dict[str, Any], *, serial_mod: Any = None) -> Dict[str, Any]:
    cfg = dict(params or {}) if isinstance(params, dict) else {}
    out = control_reset_serial.run(
        cfg,
        action_type="control.download_mode.serial_assist",
        serial_mod=serial_mod,
    )
    if out.get("ok"):
        return {
            "ok": True,
            "method": "rts_reset",
            "message": "RTS reset pulse sent",
            "action_type": "control.download_mode.serial_assist",
            "result": out,
        }
    return {
        "ok": False,
        "method": "rts_reset",
        "message": str(out.get("error_summary") or "download mode assist failed"),
        "action_type": "control.download_mode.serial_assist",
        "result": out,
    }
