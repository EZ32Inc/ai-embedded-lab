import os
import re
import time


def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _default_patterns(profile: str):
    espidf_fatal = [
        r"Guru Meditation",
        r"panic",
        r"abort\(\)",
        r"assert failed",
        r"Brownout",
        r"TWDT",
        r"Task watchdog",
        r"LoadProhibited|StoreProhibited|InstrFetchProhibited|IllegalInstruction",
        r"Rebooting\.\.\.",
    ]
    stm32_fatal = [
        r"HardFault",
        r"BusFault",
        r"MemManage",
        r"UsageFault",
        r"assert_failed",
        r"watchdog",
        r"stack overflow",
    ]
    rp2040_fatal = [
        r"\bPANIC\b",
        r"assert",
        r"hard fault",
        r"watchdog",
        r"reboot",
        r"bootrom",
    ]

    error_patterns = [
        r"\bE\s*\(",
        r"\bERROR\b",
        r"failed",
        r"failure",
        r"exception",
        r"corrupt",
        r"crc.*fail",
    ]
    warning_patterns = [
        r"\bW\s*\(",
        r"\bWARN(?:ING)?\b",
        r"deprecated",
        r"retry",
    ]

    boot_espidf = [r"rst:0x", r"ESP-ROM:", r"ESP-IDF v", r"boot:0x"]

    if profile == "espidf":
        fatal = espidf_fatal
        boot = boot_espidf
    elif profile == "stm32":
        fatal = stm32_fatal
        boot = []
    elif profile == "rp2040":
        fatal = rp2040_fatal
        boot = []
    else:
        # auto: use union of fatal patterns; boot signatures chosen after log scan
        fatal = espidf_fatal + stm32_fatal + rp2040_fatal
        boot = []

    return {
        "fatal": fatal,
        "errors": error_patterns,
        "warnings": warning_patterns,
        "boot": boot,
        "boot_espidf": boot_espidf,
    }


def _is_download_mode(lines):
    for line in lines:
        if "waiting for download" in line.lower():
            return True
    return False


def _open_capture_serial(serial_mod, port, baud):
    return serial_mod.Serial(
        port,
        baudrate=baud,
        timeout=0.1,
        rtscts=False,
        dsrdtr=False,
    )


def _capture_bytes(serial_mod, port, baud, duration_s, startup_wait_s, start_delay_s):
    open_deadline = time.time() + max(0.0, startup_wait_s)
    ser = None
    last_exc = None
    while time.time() <= open_deadline:
        try:
            ser = _open_capture_serial(serial_mod, port, baud)
            break
        except Exception as exc:
            last_exc = exc
            time.sleep(0.2)
    if ser is None:
        return None, last_exc

    data = bytearray()
    if start_delay_s > 0:
        time.sleep(start_delay_s)
    try:
        start = time.time()
        while time.time() - start < duration_s:
            chunk = ser.read(4096)
            if chunk:
                data.extend(chunk)
            else:
                time.sleep(0.01)
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return data, None


def _try_esp32_rts_reset(serial_mod, port):
    # ESP32 USB CDC boards often expose EN reset via RTS. Pulse RTS then release.
    ser = _open_capture_serial(serial_mod, port, 115200)
    try:
        try:
            ser.dtr = False
        except Exception:
            pass
        try:
            ser.rts = True
            time.sleep(0.12)
            ser.rts = False
            time.sleep(0.35)
        except Exception:
            return False, "failed to toggle RTS"
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return True, "RTS reset pulse sent"


def _evaluate_capture(text, data, port, baud, raw_log_path, profile, expect_patterns, forbid_patterns, boot_signatures):
    lines = text.splitlines()
    defaults = _default_patterns(profile)
    fatal_patterns = defaults["fatal"]
    error_patterns = defaults["errors"]
    warning_patterns = defaults["warnings"]
    boot_patterns = defaults["boot"]

    # Auto profile boot signatures for ESP-IDF if detected in log
    if profile == "auto" and not boot_signatures:
        if any("ESP-IDF" in line or "ESP-ROM" in line or "rst:0x" in line for line in lines):
            boot_patterns = defaults["boot_espidf"]

    if boot_signatures:
        boot_patterns = boot_signatures

    fatal_re = _compile(fatal_patterns)
    error_re = _compile(error_patterns)
    warning_re = _compile(warning_patterns)
    expect_re = _compile(expect_patterns)
    forbid_re = _compile(forbid_patterns)
    boot_re = _compile(boot_patterns)

    errors = []
    warnings = []
    matched_expect = {}
    matched_forbid = {}
    crash_detected = False
    reboot_loop_suspected = False
    boot_count = 0

    for idx, line in enumerate(lines, 1):
        for pat in fatal_re:
            if pat.search(line):
                crash_detected = True
                errors.append({"pattern": pat.pattern, "line": line, "lineno": idx})
        for pat in error_re:
            if pat.search(line):
                errors.append({"pattern": pat.pattern, "line": line, "lineno": idx})
        for pat in warning_re:
            if pat.search(line):
                warnings.append({"pattern": pat.pattern, "line": line, "lineno": idx})
        for pat in expect_re:
            if pat.search(line):
                matched_expect[pat.pattern] = matched_expect.get(pat.pattern, 0) + 1
        for pat in forbid_re:
            if pat.search(line):
                matched_forbid[pat.pattern] = matched_forbid.get(pat.pattern, 0) + 1
        for pat in boot_re:
            if pat.search(line):
                boot_count += 1

    if boot_count >= 2:
        reboot_loop_suspected = True
    if boot_count >= 3:
        crash_detected = True

    missing_expect = [p for p in expect_patterns if p not in matched_expect]
    forbid_matched = list(matched_forbid.keys())

    ok = True
    error_summary = ""
    if crash_detected:
        ok = False
        error_summary = "crash detected in UART log"
    elif forbid_matched:
        ok = False
        error_summary = "forbidden UART patterns matched"
    elif missing_expect:
        ok = False
        error_summary = "expected UART patterns missing"
    elif errors:
        ok = False
        error_summary = "UART error patterns detected"

    return {
        "ok": ok,
        "bytes": len(data),
        "lines": len(lines),
        "port": port,
        "baud": baud,
        "crash_detected": crash_detected,
        "reboot_loop_suspected": reboot_loop_suspected,
        "errors": errors,
        "warnings": warnings,
        "matched": {
            "expect": matched_expect,
            "forbid": matched_forbid,
            "boot": {"count": boot_count, "patterns": boot_patterns},
        },
        "missing_expect": missing_expect,
        "forbid_matched": forbid_matched,
        "raw_log_path": raw_log_path,
        "error_summary": error_summary,
        "download_mode_detected": _is_download_mode(lines),
    }


def run(cfg, raw_log_path: str):
    try:
        import serial  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pyserial is required. Install with: pip install pyserial") from exc

    enabled = bool(cfg.get("enabled", False))
    if not enabled:
        return {
            "ok": True,
            "bytes": 0,
            "lines": 0,
            "port": "",
            "baud": 0,
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "errors": [],
            "warnings": [],
            "matched": {},
            "raw_log_path": raw_log_path,
        }

    port = cfg.get("port")
    if not port:
        return {
            "ok": False,
            "bytes": 0,
            "lines": 0,
            "port": "",
            "baud": int(cfg.get("baud", 115200)),
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "errors": [],
            "warnings": [],
            "matched": {},
            "raw_log_path": raw_log_path,
            "error_summary": "UART port not set",
        }

    baud = int(cfg.get("baud", 115200))
    duration_s = float(cfg.get("duration_s", 6))
    profile = str(cfg.get("profile", "auto")).lower()
    expect_patterns = cfg.get("expect_patterns") or []
    forbid_patterns = cfg.get("forbid_patterns") or []
    boot_signatures = cfg.get("boot_signatures") or []

    if not os.path.exists(port):
        return {
            "ok": False,
            "bytes": 0,
            "lines": 0,
            "port": port,
            "baud": baud,
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "errors": [],
            "warnings": [],
            "matched": {},
            "raw_log_path": raw_log_path,
            "error_summary": f"UART port not found: {port}",
        }
    if not (os.access(port, os.R_OK) and os.access(port, os.W_OK)):
        return {
            "ok": False,
            "bytes": 0,
            "lines": 0,
            "port": port,
            "baud": baud,
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "errors": [],
            "warnings": [],
            "matched": {},
            "raw_log_path": raw_log_path,
            "error_summary": (
                f"UART permission check failed for {port}. "
                "Please fix serial device permission/group manually, then rerun."
            ),
        }

    auto_reset_on_download = bool(cfg.get("auto_reset_on_download", True))
    reset_strategy = str(cfg.get("reset_strategy", "none")).lower()

    startup_wait_s = float(cfg.get("startup_wait_s", 6.0))
    start_delay_s = float(cfg.get("start_delay_s", 0.4))
    data, last_exc = _capture_bytes(serial, port, baud, duration_s, startup_wait_s, start_delay_s)
    if data is None:
        return {
            "ok": False,
            "bytes": 0,
            "lines": 0,
            "port": port,
            "baud": baud,
            "crash_detected": False,
            "reboot_loop_suspected": False,
            "errors": [],
            "warnings": [],
            "matched": {},
            "raw_log_path": raw_log_path,
            "error_summary": f"failed to open UART port: {last_exc}",
        }

    with open(raw_log_path, "wb") as f:
        f.write(data)

    text = data.decode("utf-8", errors="replace")
    result = _evaluate_capture(
        text=text,
        data=data,
        port=port,
        baud=baud,
        raw_log_path=raw_log_path,
        profile=profile,
        expect_patterns=expect_patterns,
        forbid_patterns=forbid_patterns,
        boot_signatures=boot_signatures,
    )

    if result.get("download_mode_detected") and auto_reset_on_download and reset_strategy == "rts":
        reset_ok, reset_msg = _try_esp32_rts_reset(serial, port)
        if reset_ok:
            data2, last_exc2 = _capture_bytes(serial, port, baud, duration_s, startup_wait_s, start_delay_s)
            if data2 is not None:
                with open(raw_log_path, "wb") as f:
                    f.write(data2)
                result2 = _evaluate_capture(
                    text=data2.decode("utf-8", errors="replace"),
                    data=data2,
                    port=port,
                    baud=baud,
                    raw_log_path=raw_log_path,
                    profile=profile,
                    expect_patterns=expect_patterns,
                    forbid_patterns=forbid_patterns,
                    boot_signatures=boot_signatures,
                )
                result2["recovery"] = {
                    "attempted": True,
                    "method": "rts_reset",
                    "message": reset_msg,
                    "recovered": not result2.get("download_mode_detected", False),
                }
                return result2
            result["recovery"] = {
                "attempted": True,
                "method": "rts_reset",
                "message": f"{reset_msg}; recapture failed: {last_exc2}",
                "recovered": False,
            }
        else:
            result["recovery"] = {
                "attempted": True,
                "method": "rts_reset",
                "message": reset_msg,
                "recovered": False,
            }
        result["ok"] = False
        result["error_summary"] = "target is in download mode; reset attempted but UART expect still missing"

    return result
