#!/usr/bin/env python3
"""
esp32_minimal_bringup_template.py
==================================
Parameterized experiment runner for the Minimal-Instrument Board Bring-up Pattern.

Usage
-----
Copy this file and fill in the BOARD CONFIG section for the new target.
Replace EXPECTED test tags to match the firmware's output format.
No other changes required for a standard 7-test ESP32 suite.

See docs/esp32_bringup_civilization_pattern_v1.md for full pattern description.

Validated on:
  ESP32-C6  experiments/esp32c6_suite_ext.py
  ESP32-C5  experiments/esp32c5_suite_ext.py
"""

import glob
import os
import re
import subprocess
import sys
import threading
import time

# ── BOARD CONFIG ──────────────────────────────────────────────────────────────
# Fill these in for each new board.  Everything else is reusable as-is.

BOARD_NAME     = "esp32cX"                     # human-readable label
FIRMWARE_DIR   = ""                            # path to idf project dir
BUILD_DIR      = ""                            # path to build artefacts dir

# Serial numbers — never use /dev/ttyACMx directly; numbers shift after flash.
FLASH_SERIAL   = ""   # native USB Serial/JTAG  (MAC or USB serial string)
CONSOLE_SERIAL = ""   # CH341 UART bridge serial (or second native USB)

# Adjust timeout for BLE scan duration + WiFi + boot delay + margin.
UART_TIMEOUT_S = 35.0
WAIT_TIMEOUT_S = 40.0

# Tags that MUST appear in UART output. Order must match firmware test sequence.
EXPECTED = [
    "AEL_TEMP",
    "AEL_NVS",
    "AEL_WIFI",
    "AEL_BLE",
    "AEL_SLEEP",
    "AEL_PWM",
    "AEL_PCNT",
]

# Sentinel line that marks suite completion.
DONE_SENTINEL = "AEL_SUITE_EXT DONE"

# ── PORT DISCOVERY ────────────────────────────────────────────────────────────

def find_port_by_serial(serial: str) -> str | None:
    """
    Walk sysfs to find /dev/ttyACM* or /dev/ttyUSB* by USB serial number.
    Works for both MAC-style serials (Espressif native USB) and alphanumeric
    serials (CH341 / CP210x bridges).
    Resilient to /dev/ttyACMx number shifts that occur after each flash.
    """
    serial_norm = serial.strip().lower()
    for tty in sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")):
        base = os.path.basename(tty)
        cur  = os.path.realpath(f"/sys/class/tty/{base}/device")
        for _ in range(7):
            sp = os.path.join(cur, "serial")
            if os.path.exists(sp):
                try:
                    with open(sp) as f:
                        if f.read().strip().lower() == serial_norm:
                            return tty
                except OSError:
                    pass
                break
            cur = os.path.dirname(cur)
    return None

# ── RESET ─────────────────────────────────────────────────────────────────────

def normal_boot_reset(port: str) -> None:
    """
    Normal-boot reset via CH341 DTR/RTS lines.
    DTR=low  → BOOT pin high (normal boot, not download mode).
    RTS=high → EN pin low  (hold in reset).
    After 120 ms: RTS=low → EN pin high (release reset).

    Must be issued BEFORE starting the UART reader thread.
    Firmware's 2-second vTaskDelay gives time to open the port.
    """
    import serial as _s
    s = _s.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
    s.setDTR(False)
    s.setRTS(True)
    time.sleep(0.12)
    s.setRTS(False)
    s.close()

# ── BUILD / FLASH ─────────────────────────────────────────────────────────────

def build_firmware() -> None:
    print(f"[BUILD] {BOARD_NAME} …")
    os.makedirs(BUILD_DIR, exist_ok=True)
    r = subprocess.run(
        ["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR, "build"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout[-4000:])
        print(r.stderr[-4000:])
        raise RuntimeError("Build FAILED")
    print("[BUILD] OK")


def flash_firmware(port: str) -> None:
    print(f"[FLASH] → {port} …")
    r = subprocess.run(
        ["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR,
         "-p", port, "-b", "460800", "flash"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout[-4000:])
        print(r.stderr[-4000:])
        raise RuntimeError("Flash FAILED")
    print("[FLASH] OK")

# ── UART READER ───────────────────────────────────────────────────────────────

def read_uart_until_done(port: str, timeout_s: float = UART_TIMEOUT_S) -> list[str]:
    """
    Stream UART output until DONE_SENTINEL or timeout.
    Returns all decoded lines (including the sentinel).
    """
    import serial as _s
    lines: list[str] = []
    try:
        s = _s.Serial(port, 115200, timeout=0.2, rtscts=False, dsrdtr=False)
        deadline = time.time() + timeout_s
        buf = b""
        while time.time() < deadline:
            chunk = s.read(512)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    text = raw.decode("utf-8", errors="replace").rstrip("\r")
                    if text:
                        lines.append(text)
                        print(f"[UART] {text}")
                    if DONE_SENTINEL in text:
                        s.close()
                        return lines
        s.close()
    except Exception as exc:
        print(f"[UART] error: {exc}")
    return lines

# ── RESULT PARSING ────────────────────────────────────────────────────────────

def parse_results(uart_lines: list[str]) -> dict[str, str]:
    """
    Extract PASS/FAIL verdict for each expected tag.
    Pattern: <TAG> <detail…> PASS|FAIL  (end of line)
    """
    results: dict[str, str] = {}
    for line in uart_lines:
        for key in EXPECTED:
            m = re.search(rf"{key}\s+(.*?)(PASS|FAIL)$", line)
            if m and key not in results:
                results[key] = m.group(2)
                print(f"  {key:12} {m.group(1).strip():50s} [{m.group(2)}]")
    return results

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> int:
    build_firmware()

    flash_port = find_port_by_serial(FLASH_SERIAL)
    if not flash_port:
        print(f"[ERROR] Flash port not found ({FLASH_SERIAL})")
        return 2
    print(f"[PORT] Flash: {flash_port}")

    flash_firmware(flash_port)

    # Wait for USB re-enumeration after flash
    time.sleep(2.5)

    console_port = find_port_by_serial(CONSOLE_SERIAL)
    if not console_port:
        print(f"[ERROR] Console port not found ({CONSOLE_SERIAL})")
        return 2
    print(f"[PORT] Console: {console_port}")

    # Reset BEFORE starting UART reader — firmware 2s boot delay gives time to open port
    print("[RESET] Normal-boot reset …")
    normal_boot_reset(console_port)

    uart_lines: list[str] = []
    uart_done  = threading.Event()

    def _uart_worker():
        uart_lines.extend(read_uart_until_done(console_port, timeout_s=UART_TIMEOUT_S))
        uart_done.set()

    threading.Thread(target=_uart_worker, daemon=True).start()
    uart_done.wait(timeout=WAIT_TIMEOUT_S)

    print("\n=== Test results ===")
    results = parse_results(uart_lines)

    done_lines = [l for l in uart_lines if DONE_SENTINEL in l]
    if done_lines:
        print(f"  {'SUITE':12} {done_lines[0]}")
    else:
        print(f"  WARNING: {DONE_SENTINEL} not received")

    print()
    missing = [k for k in EXPECTED if k not in results]
    failed  = [k for k, v in results.items() if v != "PASS"]
    if missing or failed:
        if missing: print(f"OVERALL: FAIL  missing={missing}")
        if failed:  print(f"OVERALL: FAIL  failed={failed}")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
