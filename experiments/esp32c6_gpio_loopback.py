#!/usr/bin/env python3
"""
esp32c6_gpio_loopback.py
Builds, flashes, resets, and verifies the ESP32-C6 GPIO loopback experiment.

Wire pairs under test:
  A: GPIO3 (out) -> GPIO2 (in)   LA: P0.1=GPIO3(drv), P0.0=GPIO2(rdb)
  B: GPIO4 (out) -> GPIO5 (in)   LA: P0.2=GPIO5(rdb)
  C: GPIO6 (out) -> GPIO7 (in)   LA: P0.3=GPIO6(drv)

ESP32JTAG LA at 192.168.2.109, credentials admin/admin.
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

# ---- paths ----
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, "firmware", "targets", "esp32c6_gpio_loopback")
BUILD_DIR    = os.path.join(PROJECT_ROOT, "artifacts", "build_esp32c6_gpio_loopback")

# ---- hardware serials ----
FLASH_SERIAL   = "40:4C:CA:55:5A:D4"   # Espressif native USB-Serial/JTAG
CONSOLE_SERIAL = "58CF083460"           # CH341 UART0

# ---- LA ----
LA_BASE = "https://192.168.2.109"
LA_AUTH = HTTPBasicAuth("admin", "admin")

# ---- LA channel -> GPIO mapping (verified, post-test toggle observation) ----
LA_CHANNELS = {
    0: "GPIO2 (P0.0) — not driven in this test",
    1: "GPIO3 (P0.1) — toggle ~50 Hz post-test",
    2: "GPIO5 (P0.2) — toggle ~100 Hz post-test",
    3: "GPIO6 (P0.3) — toggle ~200 Hz post-test",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

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
    """Normal-boot reset via CH341 RTS/DTR."""
    import serial as _serial
    s = _serial.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
    s.setDTR(False)   # BOOT pin HIGH -> normal boot
    s.setRTS(True)    # EN LOW -> assert reset
    time.sleep(0.12)
    s.setRTS(False)   # EN HIGH -> release reset
    s.close()


def build_firmware() -> None:
    print("[BUILD] Building esp32c6_gpio_loopback …")
    os.makedirs(BUILD_DIR, exist_ok=True)
    cmd = ["idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR, "build"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-4000:])
        print(r.stderr[-4000:])
        raise RuntimeError("Build FAILED")
    print("[BUILD] OK")


def flash_firmware(flash_port: str) -> None:
    print(f"[FLASH] Flashing to {flash_port} …")
    cmd = [
        "idf.py", "-C", FIRMWARE_DIR, "-B", BUILD_DIR,
        "-p", flash_port, "-b", "460800", "flash",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-4000:])
        print(r.stderr[-4000:])
        raise RuntimeError("Flash FAILED")
    print("[FLASH] OK")


def read_uart_until_done(port: str, timeout_s: float = 12.0) -> list[str]:
    """Read UART lines until AEL_LOOPBACK DONE or timeout."""
    import serial as _serial
    lines = []
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
                    if "AEL_LOOPBACK DONE" in text:
                        s.close()
                        return lines
    except Exception as exc:
        print(f"[UART] error: {exc}")
    return lines


def la_instant_capture() -> list[int] | None:
    """Return edge counts per bit (16 bits) from instant capture."""
    sys.path.insert(0, PROJECT_ROOT)
    from ael.verification.la_verify import instant_capture, parse_samples, edge_counts_all_bits
    try:
        blob = instant_capture(LA_BASE, LA_AUTH, verify_ssl=False)
        words = parse_samples(blob)
        return edge_counts_all_bits(words)
    except Exception as exc:
        print(f"[LA] capture failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1. Build
    build_firmware()

    # 2. Find flash port
    flash_port = find_port_by_serial(FLASH_SERIAL)
    if not flash_port:
        print(f"[ERROR] Flash port not found (serial {FLASH_SERIAL})")
        return 2
    print(f"[PORT] Flash: {flash_port}")

    # 3. Flash
    flash_firmware(flash_port)

    # 4. Find console port (wait for USB re-enumeration after flash)
    time.sleep(2.5)
    console_port = find_port_by_serial(CONSOLE_SERIAL)
    if not console_port:
        print(f"[ERROR] Console port not found (serial {CONSOLE_SERIAL})")
        return 2
    print(f"[PORT] Console: {console_port}")

    # 5. Issue normal-boot reset via CH341
    #    (idf.py hard_reset on native USB does not control BOOT/EN pins reliably)
    print("[RESET] Normal-boot reset via CH341 …")
    normal_boot_reset(console_port)

    # 6. Start UART reader immediately after reset.
    #    Firmware has a 2-second vTaskDelay before printing anything, which gives
    #    the thread enough time to open the port before any output arrives.
    uart_lines: list[str] = []
    uart_done = threading.Event()

    def _uart_worker():
        uart_lines.extend(read_uart_until_done(console_port, timeout_s=14.0))
        uart_done.set()

    t_uart = threading.Thread(target=_uart_worker, daemon=True)
    t_uart.start()

    # 7. Wait for DONE (boot 2 s + tests ~120 ms)
    uart_done.wait(timeout=16.0)

    # 8. Small delay so the board has entered toggle mode, then LA capture
    time.sleep(0.5)
    print("[LA] Taking instant capture …")
    la_counts = la_instant_capture()

    # 8. Parse UART loopback results
    print("\n=== UART / loopback results ===")
    pair_results: dict[str, dict] = {}
    done_line = ""
    for line in uart_lines:
        m = re.match(
            r"AEL_LOOPBACK pair=(\w) out=GPIO(\d+) in=GPIO(\d+) "
            r"hi_rd=(\d) lo_rd=(\d) (\w+)",
            line,
        )
        if m:
            pair_results[m.group(1)] = {
                "out":    int(m.group(2)),
                "in":     int(m.group(3)),
                "hi_rd":  int(m.group(4)),
                "lo_rd":  int(m.group(5)),
                "result": m.group(6),
            }
        if "AEL_LOOPBACK DONE" in line:
            done_line = line

    for pair, r in sorted(pair_results.items()):
        ok_sym = "PASS" if r["result"] == "PASS" else "FAIL"
        print(f"  Pair {pair}: GPIO{r['out']} -> GPIO{r['in']}  "
              f"hi_rd={r['hi_rd']} lo_rd={r['lo_rd']}  [{ok_sym}]")
    if done_line:
        print(f"  {done_line}")
    else:
        print("  WARNING: AEL_LOOPBACK DONE not received")

    # 9. LA results
    print("\n=== LA results ===")
    if la_counts is not None:
        for bit, desc in LA_CHANNELS.items():
            e = la_counts[bit]
            note = "toggling" if e > 4 else ("no signal" if e == 0 else f"only {e} edges")
            print(f"  bit{bit} ({desc}): {e} edges  [{note}]")
    else:
        print("  LA capture unavailable")

    # 10. Overall verdict
    print()
    expected_pairs = {"A", "B", "C"}
    missing = expected_pairs - set(pair_results.keys())
    failed_pairs = [p for p, r in pair_results.items() if r["result"] != "PASS"]

    if missing:
        print(f"OVERALL: FAIL  (missing results for pairs: {sorted(missing)})")
        return 1
    if failed_pairs:
        print(f"OVERALL: FAIL  (failed pairs: {sorted(failed_pairs)})")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
