from __future__ import annotations

from typing import Any, Dict

from ael import failure_recovery


def evaluate_signal_facts(facts: Dict[str, Any] | Any) -> Dict[str, Any]:
    f = dict(facts) if isinstance(facts, dict) else {}
    if not bool(f.get("observe_ok", False)):
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            "error_summary": "observe failed",
            "recovery_hint": None,
        }
    if not bool(f.get("has_capture", False)):
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
            "error_summary": "verify failed",
            "recovery_hint": None,
        }
    if not bool(f.get("measure_ok", False)):
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISMATCH,
            "error_summary": "verify failed",
            "recovery_hint": None,
        }
    return {
        "ok": True,
        "failure_kind": "",
        "error_summary": "",
        "recovery_hint": None,
    }


def evaluate_uart_facts(facts: Dict[str, Any] | Any, cfg: Dict[str, Any] | Any = None) -> Dict[str, Any]:
    f = dict(facts) if isinstance(facts, dict) else {}
    cfg_d = dict(cfg) if isinstance(cfg, dict) else {}
    ok = bool(f.get("ok", False))
    error_summary = str(f.get("error_summary") or "uart observe failed")
    if ok:
        return {"ok": True, "failure_kind": "", "error_summary": "", "recovery_hint": None}

    err_l = error_summary.lower()
    if any(t in err_l for t in ("permission", "port not found", "failed to open", "cannot open", "could not open")):
        kind = failure_recovery.FAILURE_TRANSPORT_ERROR
    elif bool(f.get("download_mode_detected")):
        kind = failure_recovery.FAILURE_VERIFICATION_MISS
    else:
        kind = failure_recovery.FAILURE_VERIFICATION_MISMATCH

    hint = None
    if bool(f.get("download_mode_detected")):
        hint = failure_recovery.make_recovery_hint(
            kind=kind,
            recoverable=True,
            preferred_action="reset.serial",
            reason="uart download mode detected",
            params={"port": cfg_d.get("port"), "baud": cfg_d.get("baud", 115200)},
        )
    return {"ok": False, "failure_kind": kind, "error_summary": error_summary, "recovery_hint": hint}


def evaluate_instrument_signature_facts(facts: Dict[str, Any] | Any) -> Dict[str, Any]:
    f = dict(facts) if isinstance(facts, dict) else {}
    if not bool(f.get("backend_ready", True)):
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_INSTRUMENT_NOT_READY,
            "error_summary": str(f.get("error_summary") or "instrument not ready"),
            "recovery_hint": None,
        }
    if int(f.get("mismatch_count", 0)) > 0:
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISMATCH,
            "error_summary": "instrument digital verification failed",
            "recovery_hint": None,
        }
    return {"ok": True, "failure_kind": "", "error_summary": "", "recovery_hint": None}
