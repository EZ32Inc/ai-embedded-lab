#!/usr/bin/env python3
"""
esp32c6_hw_suite.py
Builds, flashes, and verifies all three ESP32-C6 hardware experiments in one run.

Connections:
  GPIO20 <--> GPIO21   — GPIO digital loopback
  GPIO18 <--> GPIO19   — UART1 TX/RX loopback
  GPIO22 <--> GPIO4    — ADC loopback (GPIO22 drives, GPIO4=ADC1_CH4)
  LA wires unchanged:  GPIO2/3/5/6 -> ESP32JTAG P0.0-P0.3
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

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, "firmware", "targets", "esp32c6_hw_suite")
BUILD_DIR    = os.path.join(PROJECT_ROOT, "artifacts", "build_esp32c6_hw_suite")

FLASH_SERIAL   = "40:4C:CA:55:5A:D4"
CONSOLE_SERIAL = "58CF083460"

LA_BASE = "https://192.168.2.109"
LA_AUTH = HTTPBasicAuth("admin", "admin")

LA_CHANNELS = {
    0: "GPIO2 (P0.0) — unused this test",
    1: "GPIO3 (P0.1) — toggle ~50 Hz",
    2: "GPIO5 (P0.2) — toggle ~100 Hz",
    3: "GPIO6 (P0.3) — toggle ~200 Hz",
}


def find_port_by_serial(serial: str) -> str | None:
    serial_norm = serial.strip().lower()
    for tty in sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")):
        base = os.path.basename(tty)
        cur = os.path.realpath(f"/sys/class/tty/{base}/device")
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
    import serial as _serial
    s = _serial.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
    s.setDTR(False)
    s.setRTS(True)
    time.sleep(0.12)
    s.setRTS(False)
    s.close()


def build_firmware() -> None:
    print("[BUILD] Building esp32c6_hw_suite …")
    os.makedirs(BUILD_DIR, exist_ok=True)
    r = subprocess.run(
        ["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR, "build"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:])
        raise RuntimeError("Build FAILED")
    print("[BUILD] OK")


def flash_firmware(flash_port: str) -> None:
    print(f"[FLASH] Flashing to {flash_port} …")
    r = subprocess.run(
        ["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR,
         "-p", flash_port, "-b", "460800", "flash"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:])
        raise RuntimeError("Flash FAILED")
    print("[FLASH] OK")


def read_uart_until_done(port: str, timeout_s: float = 14.0) -> list[str]:
    import serial as _serial
    lines: list[str] = []
    try:
        s = _serial.Serial(port, 115200, timeout=0.2, rtscts=False, dsrdtr=False)
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
                    if "AEL_SUITE DONE" in text:
                        s.close()
                        return lines
        s.close()
    except Exception as exc:
        print(f"[UART] error: {exc}")
    return lines


def la_instant_capture() -> list[int] | None:
    sys.path.insert(0, PROJECT_ROOT)
    from ael.verification.la_verify import instant_capture, parse_samples, edge_counts_all_bits
    try:
        blob = instant_capture(LA_BASE, LA_AUTH, verify_ssl=False)
        words = parse_samples(blob)
        return edge_counts_all_bits(words)
    except Exception as exc:
        print(f"[LA] capture failed: {exc}")
        return None


def main() -> int:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    build_firmware()

    flash_port = find_port_by_serial(FLASH_SERIAL)
    if not flash_port:
        print(f"[ERROR] Flash port not found ({FLASH_SERIAL})")
        return 2
    print(f"[PORT] Flash: {flash_port}")

    flash_firmware(flash_port)

    time.sleep(2.5)
    console_port = find_port_by_serial(CONSOLE_SERIAL)
    if not console_port:
        print(f"[ERROR] Console port not found ({CONSOLE_SERIAL})")
        return 2
    print(f"[PORT] Console: {console_port}")

    print("[RESET] Normal-boot reset via CH341 …")
    normal_boot_reset(console_port)

    uart_lines: list[str] = []
    uart_done = threading.Event()

    def _uart_worker():
        uart_lines.extend(read_uart_until_done(console_port, timeout_s=14.0))
        uart_done.set()

    threading.Thread(target=_uart_worker, daemon=True).start()
    uart_done.wait(timeout=16.0)

    time.sleep(0.5)
    print("[LA] Taking instant capture …")
    la_counts = la_instant_capture()

    # ---- Parse results ----
    print("\n=== Results ===")
    results: dict[str, str] = {}

    for line in uart_lines:
        # GPIO
        m = re.search(r"AEL_GPIO.*?(PASS|FAIL)", line)
        if m:
            results["gpio"] = m.group(1)
            print(f"  GPIO loopback  : {line.split('AEL_GPIO')[1].strip()}")
        # UART
        m = re.search(r"AEL_UART.*?(PASS|FAIL)", line)
        if m:
            results["uart"] = m.group(1)
            print(f"  UART loopback  : {line.split('AEL_UART')[1].strip()}")
        # ADC
        m = re.search(r"AEL_ADC.*?(PASS|FAIL)", line)
        if m:
            results["adc"] = m.group(1)
            print(f"  ADC loopback   : {line.split('AEL_ADC')[1].strip()}")

    done_lines = [l for l in uart_lines if "AEL_SUITE DONE" in l]
    if done_lines:
        print(f"  Suite summary  : {done_lines[0]}")
    else:
        print("  WARNING: AEL_SUITE DONE not received")

    print("\n=== LA (post-test toggle) ===")
    if la_counts is not None:
        for bit, desc in LA_CHANNELS.items():
            e = la_counts[bit]
            note = "toggling" if e > 4 else ("no signal" if e == 0 else f"{e} edges only")
            print(f"  bit{bit} ({desc}): {e} edges  [{note}]")
    else:
        print("  LA capture unavailable")

    print()
    failed = [k for k, v in results.items() if v != "PASS"]
    missing = [k for k in ("gpio", "uart", "adc") if k not in results]
    if failed or missing:
        if missing:
            print(f"OVERALL: FAIL  (missing results: {missing})")
        else:
            print(f"OVERALL: FAIL  (failed: {failed})")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
