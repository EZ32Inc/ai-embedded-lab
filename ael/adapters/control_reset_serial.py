from __future__ import annotations

import time
from typing import Any, Dict


def run(params: Dict[str, Any], *, action_type: str = "control.reset.serial") -> Dict[str, Any]:
    cfg = dict(params or {}) if isinstance(params, dict) else {}
    port = str(cfg.get("port") or "").strip()
    if not port:
        return {"ok": False, "error_summary": "control.reset.serial requires params.port"}
    baud = int(cfg.get("baud", 115200))
    pulse_ms = max(20, int(cfg.get("pulse_ms", 120)))
    settle_ms = max(50, int(cfg.get("settle_ms", 350)))

    try:
        import serial  # type: ignore
    except Exception as exc:
        return {"ok": False, "error_summary": f"control.reset.serial requires pyserial: {exc}"}

    try:
        ser = serial.Serial(
            port,
            baudrate=baud,
            timeout=0.1,
            rtscts=False,
            dsrdtr=False,
        )
        try:
            try:
                ser.dtr = False
            except Exception:
                pass
            ser.rts = True
            time.sleep(pulse_ms / 1000.0)
            ser.rts = False
            time.sleep(settle_ms / 1000.0)
        finally:
            try:
                ser.close()
            except Exception:
                pass
    except Exception as exc:
        return {"ok": False, "error_summary": f"control.reset.serial failed on {port}: {exc}"}

    return {
        "ok": True,
        "action_type": str(action_type or "control.reset.serial"),
        "port": port,
        "baud": baud,
        "pulse_ms": pulse_ms,
        "settle_ms": settle_ms,
    }
