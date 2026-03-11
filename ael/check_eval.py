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
    if ok:
        return {"ok": True, "failure_kind": "", "error_summary": "", "recovery_hint": None, "failure_class": "", "verify_substage": "uart.verify"}

    error_summary = str(f.get("error_summary") or "uart observe failed")
    err_l = error_summary.lower()
    if any(t in err_l for t in ("permission", "port not found", "failed to open", "cannot open", "could not open")):
        kind = failure_recovery.FAILURE_TRANSPORT_ERROR
        failure_class = "uart_transport_unavailable"
        error_summary = "uart transport unavailable"
    elif bool(f.get("download_mode_detected")):
        kind = failure_recovery.FAILURE_VERIFICATION_MISS
        failure_class = "uart_download_mode_detected"
        error_summary = "uart indicates download mode instead of normal firmware start"
    elif not bool(f.get("firmware_ready_seen", False)):
        kind = failure_recovery.FAILURE_VERIFICATION_MISS
        failure_class = "uart_expected_patterns_missing"
        error_summary = "expected UART readiness patterns missing"
    elif bool(f.get("crash_detected")) or bool(f.get("reboot_loop_suspected")):
        kind = failure_recovery.FAILURE_VERIFICATION_MISMATCH
        failure_class = "uart_runtime_instability"
        error_summary = "uart indicates unstable DUT runtime"
    else:
        kind = failure_recovery.FAILURE_VERIFICATION_MISMATCH
        failure_class = "uart_verification_mismatch"

    hint = None
    if bool(f.get("download_mode_detected")):
        hint = failure_recovery.make_recovery_hint(
            kind=kind,
            recoverable=True,
            preferred_action="reset.serial",
            reason="uart download mode detected",
            params={"port": cfg_d.get("port"), "baud": cfg_d.get("baud", 115200)},
        )
    return {"ok": False, "failure_kind": kind, "error_summary": error_summary, "recovery_hint": hint, "failure_class": failure_class, "verify_substage": "uart.verify"}


def evaluate_instrument_signature_facts(facts: Dict[str, Any] | Any) -> Dict[str, Any]:
    f = dict(facts) if isinstance(facts, dict) else {}
    if not bool(f.get("backend_ready", True)):
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_INSTRUMENT_NOT_READY,
            "error_summary": str(f.get("error_summary") or "instrument not ready"),
            "recovery_hint": None,
            "failure_class": "instrument_backend_not_ready",
            "verify_substage": "instrument.signature",
        }
    if int(f.get("mismatch_count", 0)) > 0:
        digital_mismatches = int(f.get("digital_mismatch_count", 0) or 0)
        analog_mismatches = int(f.get("analog_mismatch_count", 0) or 0)
        if digital_mismatches and analog_mismatches:
            error_summary = "instrument digital and analog verification failed"
            failure_class = "instrument_digital_and_analog_mismatch"
        elif analog_mismatches:
            error_summary = "instrument analog verification failed"
            failure_class = "instrument_analog_mismatch"
        else:
            error_summary = "instrument digital verification failed"
            failure_class = "instrument_digital_mismatch"
        return {
            "ok": False,
            "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISMATCH,
            "error_summary": error_summary,
            "recovery_hint": None,
            "failure_class": failure_class,
            "verify_substage": "instrument.signature",
        }
    return {"ok": True, "failure_kind": "", "error_summary": "", "recovery_hint": None, "failure_class": "", "verify_substage": "instrument.signature"}
