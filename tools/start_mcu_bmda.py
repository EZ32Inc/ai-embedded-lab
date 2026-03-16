#!/usr/bin/env python3
"""
Post-flash MCU starter for ESP32JTAG / BMDA.

Problem: after GDB 'load', MCU is halted. 'detach' alone doesn't resume it.
'continue' resumes the MCU immediately, but GDB then blocks waiting for a stop
event (MCU runs forever). We intentionally kill GDB after a short timeout --
by that point the MCU is already running.

If BMDA gets stuck after the abrupt kill, we restart it via the web API
(toggle disableUsbDapCom) and retry.

Usage:
    python3 tools/start_mcu_bmda.py --ip 192.168.2.62 --port 4242 \
        --web-user admin --web-pass admin \
        --target-id 1 --retries 3 --verify-bit 0
"""

import argparse
import subprocess
import time
import socket

import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _gdb_reset(ip, port, target_id, timeout_s):
    """Attach to target and issue monitor reset.
    BMDA falls back to AIRCR software reset when nRST is NC.
    After reset MCU runs freely; BMDA disconnects and GDB exits cleanly."""
    args = [
        "arm-none-eabi-gdb", "-q", "--nx", "--batch",
        "-ex", f"target extended-remote {ip}:{port}",
        "-ex", "monitor a",
        "-ex", f"attach {target_id}",
        "-ex", "monitor reset",
    ]
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)
        out = (res.stdout or "") + (res.stderr or "")
        print(f"  GDB exited (rc={res.returncode})")
        if out.strip():
            print(f"  Output: {out.strip()}")
        return True, out
    except subprocess.TimeoutExpired as e:
        out = ""
        if e.stdout:
            out += e.stdout if isinstance(e.stdout, str) else e.stdout.decode(errors="replace")
        if e.stderr:
            out += e.stderr if isinstance(e.stderr, str) else e.stderr.decode(errors="replace")
        print(f"  GDB timed out after {timeout_s}s")
        return False, out
    except Exception as e:
        print(f"  GDB error: {e}")
        return False, str(e)


def _port_open(ip, port, timeout_s=3):
    try:
        with socket.create_connection((ip, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def _restart_bmda(ip, web_user, web_pass):
    """Restart BMDA by toggling disableUsbDapCom via web API."""
    base = f"https://{ip}:443"
    auth = HTTPBasicAuth(web_user, web_pass)

    print("  Restarting BMDA (toggle disableUsbDapCom)...")
    try:
        requests.post(f"{base}/set_credentials",
                      json={"disableUsbDapCom": False},
                      auth=auth, verify=False, timeout=10)
    except Exception as e:
        print(f"  Warning: first toggle failed: {e}")

    time.sleep(12)

    try:
        requests.post(f"{base}/set_credentials",
                      json={"disableUsbDapCom": True},
                      auth=auth, verify=False, timeout=10)
    except Exception as e:
        print(f"  Warning: second toggle failed: {e}")

    print("  Waiting for BMDA to come back up...")
    for i in range(15):
        time.sleep(2)
        if _port_open(ip, 4242):
            print(f"  BMDA port 4242 open after {(i+1)*2 + 12}s")
            return True
    print("  BMDA did not come back in time")
    return False


def _la_check(ip, web_user, web_pass, bit, min_edges=5):
    """Quick LA capture to check if a signal bit is toggling."""
    base = f"https://{ip}:443"
    auth = HTTPBasicAuth(web_user, web_pass)
    try:
        r = requests.get(f"{base}/instant_capture", auth=auth,
                         verify=False, timeout=10)
        data = list(r.content)
        words = []
        for n in range(0, len(data) - 4, 2):
            words.append(((data[n + 1]) << 8) | data[n + 2])
        if not words:
            return False, 0
        prev = (words[0] >> bit) & 1
        edges = 0
        for w in words[1:]:
            b = (w >> bit) & 1
            if b != prev:
                edges += 1
                prev = b
        return edges >= min_edges, edges
    except Exception as e:
        print(f"  LA check error: {e}")
        return False, 0


def start_mcu(ip, port, web_user, web_pass, target_id,
              continue_timeout_s, retries, verify_bit, min_edges):
    for attempt in range(1, retries + 1):
        print(f"\n--- Attempt {attempt}/{retries} ---")

        # Check BMDA available
        if not _port_open(ip, port):
            print("  Port 4242 closed, restarting BMDA...")
            if not _restart_bmda(ip, web_user, web_pass):
                print("  Could not restart BMDA, giving up")
                return False

        # Attach and issue monitor reset (AIRCR fallback when nRST NC)
        ok, out = _gdb_reset(ip, port, target_id, continue_timeout_s)
        if not ok:
            print("  GDB failed to connect")

        # Wait a moment for MCU to start running
        time.sleep(1)

        # Check if BMDA is stuck
        if not _port_open(ip, port, timeout_s=3):
            print("  BMDA stuck after GDB kill, restarting...")
            if not _restart_bmda(ip, web_user, web_pass):
                continue

        # Verify MCU is running via LA
        print(f"  Checking PA2 signal via LA (bit {verify_bit})...")
        running, edges = _la_check(ip, web_user, web_pass, verify_bit, min_edges)
        print(f"  LA edges on bit {verify_bit}: {edges} ({'PASS' if running else 'FAIL'})")
        if running:
            print("  MCU is running!")
            return True

        print("  MCU not running yet, retrying...")

    print("\nFailed to start MCU after all attempts")
    return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="192.168.2.62")
    ap.add_argument("--port", type=int, default=4242)
    ap.add_argument("--web-user", default="admin")
    ap.add_argument("--web-pass", default="admin")
    ap.add_argument("--target-id", type=int, default=1)
    ap.add_argument("--continue-timeout", type=float, default=4.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--verify-bit", type=int, default=0)
    ap.add_argument("--min-edges", type=int, default=5)
    args = ap.parse_args()

    ok = start_mcu(
        ip=args.ip,
        port=args.port,
        web_user=args.web_user,
        web_pass=args.web_pass,
        target_id=args.target_id,
        continue_timeout_s=args.continue_timeout,
        retries=args.retries,
        verify_bit=args.verify_bit,
        min_edges=args.min_edges,
    )
    exit(0 if ok else 1)
