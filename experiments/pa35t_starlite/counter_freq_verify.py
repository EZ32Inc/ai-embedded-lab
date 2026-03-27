#!/usr/bin/env python3
"""
PA35T StarLite — Counter Frequency Verification via S3JTAG Logic Analyzer
==========================================================================

DUT   : PA35T StarLite (Artix-7 xc7a35tfgg484-2)
Design: LED blink with la_ch_in[3:0] = cnt[4:1]
  la_ch_in[0] = cnt[1] → 25.000 MHz   (JM1-PIN6,  F13)
  la_ch_in[1] = cnt[2] → 12.500 MHz   (JM1-PIN8,  F14)
  la_ch_in[2] = cnt[3] →  6.250 MHz   (JM1-PIN10, D14)
  la_ch_in[3] = cnt[4] →  3.125 MHz   (JM1-PIN12, D15)

Wiring to ESP32JTAG:
  FPGA JM1-PIN6  (F13, la_ch_in[0]) → ESP32JTAG PA0
  FPGA JM1-PIN8  (F14, la_ch_in[1]) → ESP32JTAG PA1
  FPGA JM1-PIN10 (D14, la_ch_in[2]) → ESP32JTAG PA2
  FPGA JM1-PIN12 (D15, la_ch_in[3]) → ESP32JTAG PA3
  FPGA GND → ESP32JTAG GND

Test stages:
  Stage 1 — Frequency accuracy (each channel vs expected)
  Stage 2 — Duty cycle (each channel ~50%)
  Stage 3 — Ratio validation (adjacent channels 2:1)

Usage:
  python3 experiments/pa35t_starlite/counter_freq_verify.py [--ip 192.168.2.63]
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ael.adapters import observe_fpga_counter_freq

# --- Expected channels ---
CHANNELS = [
    {"pin": "PA0", "expected_hz": 25_000_000, "label": "cnt[1] 25MHz", "fpga_pin": "F13"},
    {"pin": "PA1", "expected_hz": 12_500_000, "label": "cnt[2] 12.5MHz", "fpga_pin": "F14"},
    {"pin": "PA2", "expected_hz":  6_250_000, "label": "cnt[3] 6.25MHz", "fpga_pin": "D14"},
    {"pin": "PA3", "expected_hz":  3_125_000, "label": "cnt[4] 3.125MHz", "fpga_pin": "D15"},
]

TOLERANCES = {
    "freq_tol":   0.005,   # 0.5% — well within FPGA crystal accuracy
    "duty_tol":   0.02,    # ±2%  — counter is synchronous, should be exact
    "ratio_tol":  0.005,   # 0.5% — binary divide, should be extremely tight
}


def make_probe_cfg(ip: str) -> dict:
    return {
        "ip":                      ip,
        "web_scheme":              "https",
        "web_port":                443,
        "web_user":                "admin",
        "web_pass":                "admin",
        "web_verify_ssl":          False,
        "web_suppress_ssl_warnings": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PA35T counter frequency verification")
    parser.add_argument("--ip", default="192.168.2.63", help="ESP32JTAG IP address")
    parser.add_argument("--json-out", default=None, help="Write result JSON to file")
    args = parser.parse_args()

    probe_cfg = make_probe_cfg(args.ip)

    print("=" * 60)
    print("PA35T StarLite — Counter Frequency Verification")
    print(f"  ESP32JTAG: https://{args.ip}")
    print(f"  Sample rate: {observe_fpga_counter_freq._SAMPLE_RATE_HZ/1e6:.0f} MHz")
    print("  Channels:")
    for ch in CHANNELS:
        print(f"    {ch['pin']} → {ch['label']:18s} ({ch['expected_hz']/1e6:.4f} MHz)  FPGA pin {ch['fpga_pin']}")
    print("=" * 60)

    result = observe_fpga_counter_freq.run(
        probe_cfg,
        channels=CHANNELS,
        **TOLERANCES,
    )

    print("-" * 60)
    print("Stage 1 — Frequency Accuracy")
    all_freq_ok = all(ch["freq_ok"] for ch in result["channels"])
    print(f"  {'PASS' if all_freq_ok else 'FAIL'}  (tol ±{TOLERANCES['freq_tol']*100:.1f}%)")

    print("Stage 2 — Duty Cycle")
    all_duty_ok = all(ch["duty_ok"] for ch in result["channels"])
    print(f"  {'PASS' if all_duty_ok else 'FAIL'}  (tol ±{TOLERANCES['duty_tol']*100:.1f}%)")

    print("Stage 3 — Adjacent Ratio (should be 2.000)")
    all_ratio_ok = all(r["ratio_ok"] for r in result["ratios"])
    print(f"  {'PASS' if all_ratio_ok else 'FAIL'}  (tol ±{TOLERANCES['ratio_tol']*100:.1f}%)")

    print("-" * 60)
    overall = result["ok"]
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    if result["errors"]:
        print("Errors:")
        for e in result["errors"]:
            print(f"  ! {e}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Result written to: {args.json_out}")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
