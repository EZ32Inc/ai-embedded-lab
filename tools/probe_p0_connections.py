#!/usr/bin/env python3
"""
P0 connection probe for STM32G431CBU6.

Flashes the pin-mapping firmware (each pin toggles at unique frequency),
waits for MCU to stabilize, captures all 16 LA bits, then maps each
toggling bit to its MCU pin by frequency:

  PA2 → ~500 Hz   (1 tick)
  PA3 → ~250 Hz   (2 ticks)
  PA4 → ~125 Hz   (4 ticks)
  PB3 →  ~62 Hz   (8 ticks)

Usage:
  python3 tools/probe_p0_connections.py --ip 192.168.2.62
"""

import argparse
import time
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings()

# Expected frequencies and their MCU pin names
# (min_hz, max_hz, pin_name)
FREQ_BANDS = [
    (350,  700, "PA2"),
    (175,  350, "PA3"),
    ( 88,  175, "PA4"),
    ( 40,   88, "PB3"),
]


def configure_la(base, auth, sample_rate=260000):
    channels = ["enabled"] * 16
    payload = {
        "sampleRate": sample_rate,
        "triggerEnabled": False,
        "triggerPosition": 50,
        "triggerModeOr": True,
        "captureInternalTestSignal": False,
        "channels": channels,
    }
    requests.post(f"{base}/set_la_config", json=payload,
                  auth=auth, verify=False, timeout=10)


def capture_and_analyze(base, auth, sample_rate=260000):
    r = requests.get(f"{base}/instant_capture", auth=auth,
                     verify=False, timeout=10)
    data = list(r.content)
    words = []
    for n in range(0, len(data) - 4, 2):
        words.append((data[n + 1] << 8) | data[n + 2])

    window_s = len(words) / float(sample_rate)
    results = []
    for bit in range(16):
        bits = [(w >> bit) & 1 for w in words]
        edges = sum(1 for i in range(1, len(bits)) if bits[i] != bits[i - 1])
        freq = (edges / 2.0) / window_s if edges >= 4 else 0.0
        results.append({"bit": bit, "edges": edges, "freq_hz": freq,
                         "pin": f"P0.{bit}"})
    return results, window_s


def identify_pin(freq_hz):
    for (lo, hi, name) in FREQ_BANDS:
        if lo <= freq_hz <= hi:
            return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="192.168.2.62")
    ap.add_argument("--web-user", default="admin")
    ap.add_argument("--web-pass", default="admin")
    ap.add_argument("--settle-s", type=float, default=22.0,
                    help="Seconds to wait after flash before capture")
    ap.add_argument("--no-flash", action="store_true",
                    help="Skip flash, just capture (MCU already running probe firmware)")
    args = ap.parse_args()

    base = f"https://{args.ip}:443"
    auth = HTTPBasicAuth(args.web_user, args.web_pass)

    if not args.no_flash:
        print("Flashing probe firmware via AEL...")
        import subprocess, sys, os
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        res = subprocess.run(
            [sys.executable, "-m", "ael", "run",
             "--test", "tests/plans/stm32g431_gpio_signature.json",
             "--until-stage", "flash"],
            cwd=repo, capture_output=False
        )
        print(f"Flash exit code: {res.returncode}")
        print(f"Waiting {args.settle_s}s for MCU to stabilize...")
        time.sleep(args.settle_s)
    else:
        print("Skipping flash (--no-flash). Assuming probe firmware already running.")
        time.sleep(1)

    print("\nConfiguring LA (all 16 bits, 260kHz)...")
    configure_la(base, auth)

    # Take 3 captures and average
    print("Capturing (3 samples)...\n")
    all_results = []
    for i in range(3):
        results, window_s = capture_and_analyze(base, auth)
        all_results.append(results)
        time.sleep(0.3)

    # Average edge counts
    averaged = []
    for bit in range(16):
        freqs = [all_results[j][bit]["freq_hz"] for j in range(3)]
        avg_freq = sum(freqs) / len(freqs)
        avg_edges = sum(all_results[j][bit]["edges"] for j in range(3)) / 3
        averaged.append({"bit": bit, "freq_hz": avg_freq, "edges": avg_edges})

    print(f"Window per capture: {window_s:.3f}s\n")
    print(f"{'P0 Bit':<8} {'Freq(Hz)':>10} {'Edges':>8}  {'MCU Pin':>8}  {'Status'}")
    print("-" * 55)

    mapping = {}
    for entry in averaged:
        bit = entry["bit"]
        freq = entry["freq_hz"]
        edges = entry["edges"]
        mcu_pin = identify_pin(freq) if freq > 0 else None
        status = f"→ {mcu_pin}" if mcu_pin else ("toggling?" if edges > 2 else "no signal")
        if mcu_pin:
            mapping[f"P0.{bit}"] = mcu_pin
        print(f"P0.{bit:<4}  {freq:>10.1f}  {edges:>8.1f}  {mcu_pin or '---':>8}  {status}")

    print("\n=== WIRING MAP ===")
    if mapping:
        for p0_pin, mcu_pin in sorted(mapping.items()):
            print(f"  {mcu_pin:5s} → {p0_pin}")
    else:
        print("  No signals detected. Is the MCU running the probe firmware?")

    print("\n=== YAML for board config (observe_map) ===")
    yaml_lines = []
    reverse = {v: k for k, v in mapping.items()}
    for mcu, p0 in sorted(reverse.items()):
        yaml_lines.append(f"    {mcu.lower()}: {p0}")
    if yaml_lines:
        print("  observe_map:")
        for line in yaml_lines:
            print(f"  {line}")
    else:
        print("  (no mapping found)")


if __name__ == "__main__":
    main()
