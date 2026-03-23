#!/usr/bin/env python3
"""
esp32c5_suite_ext3.py
12-test hardware suite for ESP32-C5 (extends suite_ext2 with I2C loopback).

New test vs suite_ext2:
  AEL_I2C   I2C master/slave loopback
            I2C0 master: SDA=GPIO8,  SCL=GPIO13
            I2C1 slave:  SDA=GPIO16, SCL=GPIO17
            Jumpers: GPIO8↔GPIO16, GPIO13↔GPIO17

All wiring (6 jumpers):
  GPIO2  ↔ GPIO3    PCNT + GPIO interrupt
  GPIO4  ↔ GPIO5    UART1 TX ↔ RX
  GPIO6  →  GPIO1   ADC loopback
  GPIO7  ↔ GPIO9    SPI MOSI ↔ MISO
  GPIO8  ↔ GPIO16   I2C SDA master ↔ slave
  GPIO13 ↔ GPIO17   I2C SCL master ↔ slave

Ports:
  Flash   — Native USB Serial/JTAG  3C:DC:75:84:A6:54
  Console — CH341 UART0 bridge      5AAF278818
"""

import glob
import os
import re
import subprocess
import sys
import threading
import time

_HERE        = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, "firmware", "targets", "esp32c5_suite_ext3")
BUILD_DIR    = os.path.join(PROJECT_ROOT, "artifacts",  "build_esp32c5_suite_ext3")

FLASH_SERIAL   = "3C:DC:75:84:A6:54"
CONSOLE_SERIAL = "5AAF278818"

EXPECTED = [
    "AEL_TEMP", "AEL_NVS", "AEL_WIFI", "AEL_BLE",
    "AEL_SLEEP", "AEL_PWM",
    "AEL_INTR", "AEL_PCNT",
    "AEL_UART", "AEL_ADC", "AEL_SPI", "AEL_I2C",
]
DONE_SENTINEL = "AEL_SUITE_EXT3 DONE"


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
    print("[BUILD] esp32c5_suite_ext3 …")
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


def read_uart_until_done(port: str, timeout_s: float = 50.0) -> list[str]:
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


def main() -> int:
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
        # WiFi ~12s + BLE 3s + boot 2s + 12 tests + margin = 50s
        uart_lines.extend(read_uart_until_done(console_port, timeout_s=50.0))
        uart_done.set()

    threading.Thread(target=_uart_worker, daemon=True).start()
    uart_done.wait(timeout=55.0)

    print("\n=== Test results ===")
    results: dict[str, str] = {}
    for line in uart_lines:
        for key in EXPECTED:
            m = re.search(rf"{key}\s+(.*?)(PASS|FAIL)$", line)
            if m and key not in results:
                results[key] = m.group(2)
                print(f"  {key:12} {m.group(1).strip():50s} [{m.group(2)}]")

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
