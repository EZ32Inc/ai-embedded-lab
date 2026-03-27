"""
ael.adapters.post_flash_verify
==============================
Post-flash runtime verification for ESP32 boards connected via USB-UART bridge.

Core principle
--------------
    flash success  ≠  runtime ready

idf.py / esptool reporting a successful write only means the binary was written
to flash.  The chip may have crashed, looped in the bootloader, failed to
connect to WiFi, or be running stale firmware from a previous build.

This adapter opens the UART serial port immediately after flash, captures the
boot log, and evaluates it against an expected-state profile.  Only when all
required patterns are present (and no forbidden patterns are seen) is the board
considered READY and AEL allowed to proceed to network checks or functional
tests.

If the required state is not reached, the adapter retries by issuing a hardware
reset via the USB-UART bridge RTS line (DTR=low → normal-boot mode; RTS pulse
→ reset) and recaptures the log.  If all retry attempts are exhausted the
adapter returns a result whose failure_kind is FAILURE_RUNTIME_BRINGUP_FAILED,
which is distinct from transport errors and test failures.

Config keys
-----------
    port                 str   Serial device, e.g. /dev/ttyUSB0
    baud                 int   Baud rate (default 115200)
    profile              str   "instrument_ready" | "boot_only" | "custom"
                               (default "instrument_ready")
    custom_patterns      list  Required patterns when profile="custom"
    reset_on_start       bool  Pulse RTS before first capture (default True)
                               Set False for native-USB boards where RTS/DTR
                               cannot trigger a hardware reset.
    capture_window_s     float Seconds to capture serial output (default 20.0)
    startup_wait_s       float Max seconds to wait for port to appear (default 6.0)
    heartbeat_confirm_s  float Extra window after ready anchor to confirm heartbeat
                               (default 5.0); set 0 to skip heartbeat check
    max_recovery_attempts int  Times to reset-and-retry on failure (default 2)

Return dict keys
----------------
    ok                   bool   True iff firmware reached expected state
    firmware_ready_seen  bool   True iff the ready-anchor pattern was matched
    heartbeat_confirmed  bool   True iff heartbeat was observed after ready
    state                str    "ready" | "partial" | "crash" | "no_output"
                                | "port_unavailable"
    flash_succeeded      bool   Always True (this adapter is only called post-flash)
    matched_required     list   Required patterns that were matched
    missing_required     list   Required patterns that were NOT matched
    forbidden_matched    list   Forbidden patterns that were matched (empty = good)
    crash_detected       bool
    reboot_loop_suspected bool
    download_mode_detected bool
    recovery_attempts    int    Number of reset+retry cycles performed
    elapsed_s            float
    raw_log_path         str
    failure_kind         str    failure_recovery constant, or "" on success
    error_summary        str    Human-readable failure description, or "" on success
    recovery_hint        dict | None

Example (success)
-----------------
    cfg = {
        "port": "/dev/ttyUSB0",
        "baud": 115200,
        "profile": "instrument_ready",
        "reset_on_start": True,
        "capture_window_s": 20,
        "max_recovery_attempts": 2,
    }
    result = run(cfg, raw_log_path="/tmp/post_flash.log")
    assert result["ok"]
    assert result["firmware_ready_seen"]

Example (failure)
-----------------
    if not result["ok"]:
        # result["failure_kind"] == "runtime_bringup_failed"
        # result["flash_succeeded"] == True
        # Never misreport as a network failure or instrument error.
        raise RuntimeError(result["error_summary"])
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

from ael import failure_recovery
from ael.post_flash.profiles import VerifyProfile, get_profile


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error:
            compiled.append(re.compile(re.escape(p), re.IGNORECASE))
    return compiled


def _match_all(patterns: List[re.Pattern], lines: List[str]) -> Dict[str, bool]:
    """Return {pattern.pattern: matched} for each compiled pattern."""
    results: Dict[str, bool] = {p.pattern: False for p in patterns}
    for line in lines:
        for p in patterns:
            if p.search(line):
                results[p.pattern] = True
    return results


def _any_match(patterns: List[re.Pattern], lines: List[str]) -> List[str]:
    """Return list of pattern strings that matched at least one line."""
    matched = []
    for p in patterns:
        for line in lines:
            if p.search(line):
                matched.append(p.pattern)
                break
    return matched


def _count_matches(pattern: re.Pattern, lines: List[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def _reboot_loop(lines: List[str]) -> bool:
    """Heuristic: three or more ESP-IDF boot banners → reset loop."""
    boot_re = re.compile(r"rst:0x|ESP-ROM:|boot:0x", re.IGNORECASE)
    return sum(1 for line in lines if boot_re.search(line)) >= 3


def _evaluate_against_profile(
    lines: List[str],
    profile: VerifyProfile,
    custom_patterns: List[str],
) -> Dict[str, Any]:
    """Evaluate captured lines against the profile.  Returns evaluation dict."""
    required_patterns = list(profile.required) if profile.name != "custom" else list(custom_patterns)
    forbidden_patterns = list(profile.forbidden) if profile.name != "custom" else []

    req_compiled = _compile_patterns(required_patterns)
    forb_compiled = _compile_patterns(forbidden_patterns)

    req_match = _match_all(req_compiled, lines)
    forb_matched = _any_match(forb_compiled, lines)

    matched_required = [p for p, hit in req_match.items() if hit]
    missing_required = [p for p, hit in req_match.items() if not hit]

    crash_detected = bool(forb_matched)
    reboot_loop = _reboot_loop(lines)
    if reboot_loop:
        crash_detected = True

    # firmware_ready_seen: the ready anchor was observed
    anchor_re: Optional[re.Pattern] = None
    firmware_ready_seen = False
    anchor_line_idx = -1
    if profile.firmware_ready_anchor:
        try:
            anchor_re = re.compile(profile.firmware_ready_anchor, re.IGNORECASE)
        except re.error:
            anchor_re = re.compile(re.escape(profile.firmware_ready_anchor), re.IGNORECASE)
        for idx, line in enumerate(lines):
            if anchor_re.search(line):
                firmware_ready_seen = True
                anchor_line_idx = idx
                break

    # download_mode_detected
    dl_re = re.compile(r"waiting for download|boot:0x[0-9a-f]+ \(download", re.IGNORECASE)
    download_mode_detected = any(dl_re.search(line) for line in lines)

    return {
        "matched_required": matched_required,
        "missing_required": missing_required,
        "forbidden_matched": forb_matched,
        "crash_detected": crash_detected,
        "reboot_loop_suspected": reboot_loop,
        "firmware_ready_seen": firmware_ready_seen,
        "anchor_line_idx": anchor_line_idx,
        "download_mode_detected": download_mode_detected,
        "required_all_met": len(missing_required) == 0 and len(required_patterns) > 0,
        "has_any_output": len(lines) > 0,
    }


def _open_serial(serial_mod: Any, port: str, baud: int):
    return serial_mod.Serial(
        port,
        baudrate=baud,
        timeout=0.1,
        rtscts=False,
        dsrdtr=False,
    )


def _capture_with_optional_reset(
    serial_mod: Any,
    port: str,
    baud: int,
    duration_s: float,
    startup_wait_s: float,
    do_reset: bool,
) -> tuple:
    """Open serial, optionally pulse RTS (reset), capture for duration_s.

    Returns (lines: list[str], error: str | None).

    DTR is always de-asserted before capture so the bridge chip does not hold
    GPIO0 low (which would trap the ESP32 in download mode).

    Uses readline() so that each log line is captured atomically and the
    function works correctly with both real pyserial ports and test fakes.
    The loop exits when duration_s elapses OR the port signals EOF (empty read
    with no more data expected from a one-shot fake).
    """
    # Open with retry up to startup_wait_s; always try at least once.
    open_deadline = time.monotonic() + max(0.0, startup_wait_s)
    ser = None
    last_exc: Optional[Exception] = None

    while True:
        try:
            ser = _open_serial(serial_mod, port, baud)
            break
        except Exception as exc:
            last_exc = exc
            if time.monotonic() >= open_deadline:
                break
            time.sleep(0.2)

    if ser is None:
        return [], f"failed to open {port}: {last_exc}"

    lines: List[str] = []
    consecutive_empty = 0
    try:
        # Always de-assert DTR so GPIO0 stays HIGH → normal-boot mode.
        try:
            ser.dtr = False
        except Exception:
            pass

        if do_reset:
            # RTS high → EN low (hold in reset).  RTS low → release.
            try:
                ser.rts = True
                time.sleep(0.12)
                ser.rts = False
            except Exception:
                pass
            # Brief settle so ESP32 ROM can latch GPIO0 before we read.
            time.sleep(0.35)

        t0 = time.monotonic()
        while time.monotonic() - t0 < duration_s:
            try:
                raw = ser.readline()
            except Exception:
                break
            if raw:
                consecutive_empty = 0
                line = raw.decode("utf-8", errors="replace").rstrip()
                lines.append(line)
            else:
                consecutive_empty += 1
                # After 5 consecutive empty reads consider the stream done
                # (handles test fakes that exhaust their line list).
                if consecutive_empty >= 5:
                    break
                time.sleep(0.01)
    finally:
        try:
            ser.close()
        except Exception:
            pass

    return lines, None


def _check_heartbeat(
    serial_mod: Any,
    port: str,
    baud: int,
    heartbeat_pattern: str,
    window_s: float,
) -> bool:
    """Open serial for window_s and check for at least one heartbeat line."""
    if not heartbeat_pattern or window_s <= 0:
        return False
    try:
        hb_re = re.compile(heartbeat_pattern, re.IGNORECASE)
    except re.error:
        hb_re = re.compile(re.escape(heartbeat_pattern), re.IGNORECASE)

    try:
        ser = _open_serial(serial_mod, port, baud)
    except Exception:
        return False

    found = False
    try:
        try:
            ser.dtr = False
        except Exception:
            pass
        t0 = time.monotonic()
        while time.monotonic() - t0 < window_s:
            try:
                raw = ser.readline()
            except Exception:
                break
            if not raw:
                time.sleep(0.01)
                continue
            line = raw.decode("utf-8", errors="replace").rstrip()
            if hb_re.search(line):
                found = True
                break
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return found


def _classify_state(eval_result: Dict[str, Any]) -> str:
    """Collapse evaluation dict to a single state label."""
    if not eval_result["has_any_output"]:
        return "no_output"
    if eval_result["crash_detected"]:
        return "crash"
    if eval_result["required_all_met"] and eval_result["firmware_ready_seen"]:
        return "ready"
    return "partial"


def _make_failure_result(
    *,
    state: str,
    eval_result: Dict[str, Any],
    recovery_attempts: int,
    elapsed_s: float,
    raw_log_path: str,
    port: str,
    baud: int,
    capture_lines_excerpt: List[str],
) -> Dict[str, Any]:
    """Build a failure result dict with runtime_bringup_failed failure kind."""
    if state == "port_unavailable":
        kind = failure_recovery.FAILURE_TRANSPORT_ERROR
        error_summary = f"UART port unavailable: {port}"
        failure_class = "uart_transport_unavailable"
    elif state == "no_output":
        kind = failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED
        error_summary = "flash succeeded but firmware produced no UART output"
        failure_class = "runtime_no_output"
    elif state == "crash":
        kind = failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED
        forbidden = eval_result.get("forbidden_matched") or []
        reboot = eval_result.get("reboot_loop_suspected", False)
        if reboot:
            error_summary = "flash succeeded but firmware is in a reboot loop"
            failure_class = "runtime_reboot_loop"
        elif forbidden:
            error_summary = f"flash succeeded but firmware crashed ({forbidden[0]})"
            failure_class = "runtime_crash"
        else:
            error_summary = "flash succeeded but firmware crash detected"
            failure_class = "runtime_crash"
    else:  # partial
        missing = eval_result.get("missing_required") or []
        kind = failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED
        error_summary = (
            "flash succeeded but runtime bring-up failed: "
            f"missing patterns: {missing}"
        )
        failure_class = "runtime_bringup_incomplete"

    reboot_loop = eval_result.get("reboot_loop_suspected", False)
    recoverable = not reboot_loop and state != "crash"

    hint = failure_recovery.make_recovery_hint(
        kind=kind,
        recoverable=recoverable,
        preferred_action="control.reset.serial" if recoverable else "inspect_serial_log",
        reason=error_summary,
        scope="post_flash",
        retry=recoverable,
        params={"port": port, "baud": baud},
    )
    if not recoverable:
        hint = None

    return {
        "ok": False,
        "flash_succeeded": True,
        "firmware_ready_seen": bool(eval_result.get("firmware_ready_seen", False)),
        "heartbeat_confirmed": False,
        "state": state,
        "matched_required": eval_result.get("matched_required", []),
        "missing_required": eval_result.get("missing_required", []),
        "forbidden_matched": eval_result.get("forbidden_matched", []),
        "crash_detected": bool(eval_result.get("crash_detected", False)),
        "reboot_loop_suspected": bool(eval_result.get("reboot_loop_suspected", False)),
        "download_mode_detected": bool(eval_result.get("download_mode_detected", False)),
        "recovery_attempts": recovery_attempts,
        "elapsed_s": round(elapsed_s, 3),
        "raw_log_path": raw_log_path,
        "failure_kind": failure_recovery.normalize_failure_kind(kind),
        "failure_class": failure_class,
        "error_summary": error_summary,
        "recovery_hint": hint,
        "capture_excerpt": "\n".join(capture_lines_excerpt[-20:]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(cfg: Dict[str, Any], raw_log_path: str) -> Dict[str, Any]:
    """Run post-flash runtime verification.

    Parameters
    ----------
    cfg : dict
        Verification configuration (see module docstring for keys).
    raw_log_path : str
        Path where the raw UART log will be written.

    Returns
    -------
    dict
        Result dict.  Check result["ok"] first.  On failure,
        result["failure_kind"] == "runtime_bringup_failed" (unless the serial
        port itself is unavailable, in which case it is "transport_error").
    """
    t_start = time.monotonic()

    port = str(cfg.get("port") or "").strip()
    baud = int(cfg.get("baud") or 115200)
    profile_name = str(cfg.get("profile") or "instrument_ready").strip().lower()
    custom_patterns: List[str] = list(cfg.get("custom_patterns") or [])
    reset_on_start = bool(cfg.get("reset_on_start", True))
    capture_window_s = float(cfg.get("capture_window_s") or 20.0)
    startup_wait_s = float(cfg.get("startup_wait_s") or 6.0)
    heartbeat_confirm_s = float(cfg.get("heartbeat_confirm_s") or 5.0)
    max_recovery_attempts = int(cfg.get("max_recovery_attempts") or 2)

    # ------------------------------------------------------------------
    # Resolve profile
    # ------------------------------------------------------------------
    if profile_name == "custom":
        profile = VerifyProfile(
            name="custom",
            required=custom_patterns,
            forbidden=[],
            firmware_ready_anchor=custom_patterns[0] if custom_patterns else "",
        )
    else:
        profile = get_profile(profile_name)
        if profile is None:
            # Fall back to instrument_ready rather than silently skipping
            from ael.post_flash.profiles import INSTRUMENT_READY
            profile = INSTRUMENT_READY

    # ------------------------------------------------------------------
    # Serial port availability check
    # ------------------------------------------------------------------
    if not port:
        elapsed = time.monotonic() - t_start
        return {
            "ok": False,
            "flash_succeeded": True,
            "firmware_ready_seen": False,
            "heartbeat_confirmed": False,
            "state": "port_unavailable",
            "matched_required": [],
            "missing_required": list(profile.required),
            "forbidden_matched": [],
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "download_mode_detected": False,
            "recovery_attempts": 0,
            "elapsed_s": round(elapsed, 3),
            "raw_log_path": raw_log_path,
            "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            "failure_class": "uart_transport_unavailable",
            "error_summary": "post_flash_verify: port not configured",
            "recovery_hint": None,
            "capture_excerpt": "",
        }

    try:
        import serial as _serial  # type: ignore
    except Exception as exc:  # pragma: no cover
        elapsed = time.monotonic() - t_start
        return {
            "ok": False,
            "flash_succeeded": True,
            "firmware_ready_seen": False,
            "heartbeat_confirmed": False,
            "state": "port_unavailable",
            "matched_required": [],
            "missing_required": list(profile.required),
            "forbidden_matched": [],
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "download_mode_detected": False,
            "recovery_attempts": 0,
            "elapsed_s": round(elapsed, 3),
            "raw_log_path": raw_log_path,
            "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            "failure_class": "uart_transport_unavailable",
            "error_summary": f"post_flash_verify: pyserial not installed: {exc}",
            "recovery_hint": None,
            "capture_excerpt": "",
        }

    if not os.path.exists(port):
        elapsed = time.monotonic() - t_start
        return {
            "ok": False,
            "flash_succeeded": True,
            "firmware_ready_seen": False,
            "heartbeat_confirmed": False,
            "state": "port_unavailable",
            "matched_required": [],
            "missing_required": list(profile.required),
            "forbidden_matched": [],
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "download_mode_detected": False,
            "recovery_attempts": 0,
            "elapsed_s": round(elapsed, 3),
            "raw_log_path": raw_log_path,
            "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            "failure_class": "uart_transport_unavailable",
            "error_summary": f"post_flash_verify: serial port not found: {port}",
            "recovery_hint": None,
            "capture_excerpt": "",
        }

    # ------------------------------------------------------------------
    # Capture + evaluate loop
    # ------------------------------------------------------------------
    last_lines: List[str] = []
    last_eval: Dict[str, Any] = {}
    recovery_attempts = 0

    for attempt in range(max_recovery_attempts + 1):
        do_reset = reset_on_start or (attempt > 0)
        lines, open_err = _capture_with_optional_reset(
            _serial, port, baud, capture_window_s, startup_wait_s, do_reset
        )

        if open_err and not lines:
            # Port open failed on this attempt — if there are retries left,
            # wait briefly and retry (port may still be enumerating after flash).
            if attempt < max_recovery_attempts:
                recovery_attempts += 1
                time.sleep(1.5)
                continue
            # All attempts failed to open serial.
            elapsed = time.monotonic() - t_start
            return {
                "ok": False,
                "flash_succeeded": True,
                "firmware_ready_seen": False,
                "heartbeat_confirmed": False,
                "state": "port_unavailable",
                "matched_required": [],
                "missing_required": list(profile.required),
                "forbidden_matched": [],
                "crash_detected": False,
                "reboot_loop_suspected": False,
                "download_mode_detected": False,
                "recovery_attempts": recovery_attempts,
                "elapsed_s": round(elapsed, 3),
                "raw_log_path": raw_log_path,
                "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
                "failure_class": "uart_transport_unavailable",
                "error_summary": f"post_flash_verify: {open_err}",
                "recovery_hint": None,
                "capture_excerpt": "",
            }

        last_lines = lines
        last_eval = _evaluate_against_profile(lines, profile, custom_patterns)
        state = _classify_state(last_eval)

        # Success path — check heartbeat then return
        if state == "ready":
            # Write raw log
            try:
                with open(raw_log_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            except Exception:
                pass

            heartbeat_confirmed = False
            if profile.heartbeat_pattern and heartbeat_confirm_s > 0:
                heartbeat_confirmed = _check_heartbeat(
                    _serial, port, baud, profile.heartbeat_pattern, heartbeat_confirm_s
                )

            elapsed = time.monotonic() - t_start
            return {
                "ok": True,
                "flash_succeeded": True,
                "firmware_ready_seen": True,
                "heartbeat_confirmed": heartbeat_confirmed,
                "state": "ready",
                "matched_required": last_eval["matched_required"],
                "missing_required": [],
                "forbidden_matched": [],
                "crash_detected": False,
                "reboot_loop_suspected": False,
                "download_mode_detected": bool(last_eval.get("download_mode_detected")),
                "recovery_attempts": recovery_attempts,
                "elapsed_s": round(elapsed, 3),
                "raw_log_path": raw_log_path,
                "failure_kind": "",
                "failure_class": "",
                "error_summary": "",
                "recovery_hint": None,
                "capture_excerpt": "\n".join(lines[-10:]),
            }

        # Reboot loop is not recoverable — stop retrying immediately.
        if last_eval.get("reboot_loop_suspected"):
            break

        # Otherwise retry if attempts remain.
        if attempt < max_recovery_attempts:
            recovery_attempts += 1
            # Brief pause before reset+recapture
            time.sleep(0.5)
            continue

    # ------------------------------------------------------------------
    # All attempts exhausted — write raw log and return failure
    # ------------------------------------------------------------------
    try:
        with open(raw_log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(last_lines))
    except Exception:
        pass

    elapsed = time.monotonic() - t_start
    state = _classify_state(last_eval) if last_eval else "no_output"
    return _make_failure_result(
        state=state,
        eval_result=last_eval or {},
        recovery_attempts=recovery_attempts,
        elapsed_s=elapsed,
        raw_log_path=raw_log_path,
        port=port,
        baud=baud,
        capture_lines_excerpt=last_lines,
    )
