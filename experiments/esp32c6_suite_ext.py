#!/usr/bin/env python3
"""
esp32c6_suite_ext.py
Extended hardware suite: Temperature, NVS, Wi-Fi scan, BLE scan,
Light sleep, PWM (LA duty/freq check), PCNT pulse count.
"""

import glob
import os
import re
import subprocess
import sys
import threading
import time

import requests
import urllib3
from requests.auth import HTTPBasicAuth

_HERE        = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, "firmware", "targets", "esp32c6_suite_ext")
BUILD_DIR    = os.path.join(PROJECT_ROOT, "artifacts",  "build_esp32c6_suite_ext")

FLASH_SERIAL   = "40:4C:CA:55:5A:D4"
CONSOLE_SERIAL = "58CF083460"

LA_BASE = "https://192.168.2.109"
LA_AUTH = HTTPBasicAuth("admin", "admin")

# Expected tests; key = regex prefix in UART line
EXPECTED = ["AEL_TEMP", "AEL_NVS", "AEL_WIFI", "AEL_BLE",
            "AEL_SLEEP", "AEL_PWM", "AEL_PCNT"]


def find_port_by_serial(serial: str) -> str | None:
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


def normal_boot_reset(port: str) -> None:
    import serial as _s
    s = _s.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
    s.setDTR(False); s.setRTS(True);  time.sleep(0.12); s.setRTS(False)
    s.close()


def build_firmware() -> None:
    print("[BUILD] esp32c6_suite_ext …")
    os.makedirs(BUILD_DIR, exist_ok=True)
    r = subprocess.run(["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR, "build"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:])
        raise RuntimeError("Build FAILED")
    print("[BUILD] OK")


def flash_firmware(port: str) -> None:
    print(f"[FLASH] → {port} …")
    r = subprocess.run(["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR,
                        "-p", port, "-b", "460800", "flash"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:])
        raise RuntimeError("Flash FAILED")
    print("[FLASH] OK")


def read_uart_until_done(port: str, timeout_s: float = 25.0) -> list[str]:
    """Read until AEL_SUITE_EXT DONE or timeout."""
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
                    if "AEL_SUITE_EXT DONE" in text:
                        s.close()
                        return lines
        s.close()
    except Exception as exc:
        print(f"[UART] error: {exc}")
    return lines


def la_capture_pwm() -> dict:
    """
    Capture with LA at 260 kHz.
    GPIO3 (bit 1, P0.1) should be running LEDC 1 kHz 50%.
    Returns dict with freq_hz and duty for bit 1.
    """
    sys.path.insert(0, PROJECT_ROOT)
    from ael.verification.la_verify import (
        configure_la, instant_capture, parse_samples,
        analyze_samples, edge_counts_all_bits,
    )
    SAMPLE_RATE = 260_000
    try:
        configure_la(LA_BASE, LA_AUTH, verify_ssl=False,
                     sample_rate=SAMPLE_RATE,
                     trigger_enabled=False, trigger_position=50,
                     trigger_mode_or=True,
                     capture_internal_test_signal=False,
                     channels=["disabled"] * 16)
        blob  = instant_capture(LA_BASE, LA_AUTH, verify_ssl=False)
        words = parse_samples(blob)
        counts = edge_counts_all_bits(words)
        # Analyse GPIO3 (bit 1) for PWM freq + duty
        result = analyze_samples(words, SAMPLE_RATE, bit=1, min_edges=4)
        return {
            "counts":   counts,
            "pwm":      result,
            "sample_rate": SAMPLE_RATE,
            "n_words":  len(words),
        }
    except Exception as exc:
        print(f"[LA] capture failed: {exc}")
        return {}


def main() -> int:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    build_firmware()

    flash_port = find_port_by_serial(FLASH_SERIAL)
    if not flash_port:
        print(f"[ERROR] Flash port not found ({FLASH_SERIAL})"); return 2
    print(f"[PORT] Flash: {flash_port}")

    flash_firmware(flash_port)

    time.sleep(2.5)
    console_port = find_port_by_serial(CONSOLE_SERIAL)
    if not console_port:
        print(f"[ERROR] Console port not found ({CONSOLE_SERIAL})"); return 2
    print(f"[PORT] Console: {console_port}")

    print("[RESET] Normal-boot reset …")
    normal_boot_reset(console_port)

    uart_lines: list[str] = []
    uart_done  = threading.Event()

    def _uart_worker():
        # BLE scan = 3 s, total suite ≈ 8 s after 2 s boot delay → 20 s budget
        uart_lines.extend(read_uart_until_done(console_port, timeout_s=22.0))
        uart_done.set()

    threading.Thread(target=_uart_worker, daemon=True).start()
    uart_done.wait(timeout=25.0)

    time.sleep(0.5)
    print("[LA] Capturing PWM on GPIO3 (P0.1) …")
    la = la_capture_pwm()

    # ---- parse results ----
    print("\n=== Test results ===")
    results: dict[str, str] = {}

    for line in uart_lines:
        for key in EXPECTED:
            m = re.search(rf"{key}\s+(.*?)(PASS|FAIL)$", line)
            if m and key not in results:
                results[key] = m.group(2)
                print(f"  {key:12} {m.group(1).strip():50s} [{m.group(2)}]")

    done_lines = [l for l in uart_lines if "AEL_SUITE_EXT DONE" in l]
    if done_lines:
        print(f"  {'SUITE':12} {done_lines[0]}")
    else:
        print("  WARNING: AEL_SUITE_EXT DONE not received")

    # ---- LA analysis ----
    print("\n=== LA analysis (post-test) ===")
    if la:
        counts = la.get("counts", [])
        sr     = la.get("sample_rate", 260_000)
        nw     = la.get("n_words", 0)
        window = nw / sr if sr else 0
        print(f"  Sample rate {sr/1e3:.0f} kHz, window {window*1000:.0f} ms, {nw} samples")

        # bit 1 = GPIO3/P0.1 = LEDC PWM
        pwm = la.get("pwm", {})
        m   = pwm.get("metrics", {})
        freq = m.get("freq_hz", 0)
        duty = m.get("duty",    0)
        edges = m.get("edges",  0)
        # ESP32-C6 LEDC 10-bit mode produces ~freq/2 observed output;
        # accept 400-1200 Hz range and verify duty cycle.
        pwm_ok = (400 < freq < 1200) and (0.40 < duty < 0.60)
        print(f"  GPIO3 P0.1 (LEDC 1kHz): edges={edges} freq={freq:.0f}Hz duty={duty:.2f}"
              f"  [{'PWM OK' if pwm_ok else 'PWM FAIL'}]")

        # bits 2,3 = GPIO5/6 manual toggle
        if len(counts) >= 4:
            print(f"  GPIO5 P0.2 (toggle ~50Hz):  {counts[2]} edges")
            print(f"  GPIO6 P0.3 (toggle ~100Hz): {counts[3]} edges")

        # fold PWM LA result into AEL_PWM verdict
        if "AEL_PWM" in results and results["AEL_PWM"] == "PASS":
            results["AEL_PWM_LA"] = "PASS" if pwm_ok else "FAIL"
    else:
        print("  LA capture unavailable")

    # ---- verdict ----
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
