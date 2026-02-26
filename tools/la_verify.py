#!/usr/bin/env python3
import argparse
import sys
import time
from typing import List

import requests
from requests.auth import HTTPBasicAuth


SUPPORTED_RATES = [
    264_000_000,
    132_000_000,
    66_000_000,
    33_000_000,
    22_000_000,
    16_500_000,
    11_000_000,
    6_000_000,
    3_000_000,
    2_000_000,
    1_000_000,
    500_000,
    260_000,
]


def choose_sample_rate(target_window_s: float, samples_hint: int = 65536) -> int:
    if target_window_s <= 0:
        return 1_000_000
    desired = int(samples_hint / target_window_s)
    # pick nearest supported rate
    return min(SUPPORTED_RATES, key=lambda r: abs(r - desired))


def parse_samples(buffer: bytes) -> List[int]:
    data = list(buffer)
    words = []
    for n in range(0, len(data) - 4, 2):
        low = data[n + 2]
        high = data[n + 1]
        words.append((high << 8) | low)
    return words


def extract_bit(words: List[int], bit: int) -> List[int]:
    return [(w >> bit) & 0x1 for w in words]


def count_edges(bits: List[int]) -> int:
    if not bits:
        return 0
    edges = 0
    prev = bits[0]
    for b in bits[1:]:
        if b != prev:
            edges += 1
        prev = b
    return edges


def edge_counts_all_bits(words: List[int], bits: int = 16) -> List[int]:
    counts = [0] * bits
    if not words:
        return counts
    prev = [(words[0] >> i) & 0x1 for i in range(bits)]
    for w in words[1:]:
        for i in range(bits):
            b = (w >> i) & 0x1
            if b != prev[i]:
                counts[i] += 1
                prev[i] = b
    return counts


def configure_la(base_url, auth, verify_ssl, sample_rate, trigger_enabled, trigger_position,
                 trigger_mode_or, capture_internal_test_signal, channels):
    payload = {
        "sampleRate": int(sample_rate),
        "triggerPosition": int(trigger_position),
        "triggerEnabled": bool(trigger_enabled),
        "triggerModeOR": bool(trigger_mode_or),
        "captureInternalTestSignal": bool(capture_internal_test_signal),
        "channels": channels,
    }
    r = requests.post(
        f"{base_url}/la_configure",
        json=payload,
        headers={"Content-Type": "application/json"},
        auth=auth,
        timeout=5,
        verify=verify_ssl,
    )
    r.raise_for_status()
    return r.json() if r.content else {}


def instant_capture(base_url, auth, verify_ssl) -> bytes:
    r = requests.get(f"{base_url}/instant_capture", auth=auth, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    return r.content


def triggered_capture(base_url, auth, verify_ssl, timeout_s=5.0) -> bytes:
    r = requests.get(f"{base_url}/la_start_capture", auth=auth, timeout=5, verify=verify_ssl)
    r.raise_for_status()

    start = time.time()
    while True:
        status = requests.get(f"{base_url}/la_status", auth=auth, timeout=5, verify=verify_ssl).json()
        if status.get("triggered"):
            break
        if time.time() - start > timeout_s:
            raise TimeoutError("LA trigger timeout")
        time.sleep(0.1)

    r = requests.get(f"{base_url}/capture_data", auth=auth, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    return r.content


def run(args) -> int:
    if args.dry_run:
        # simple square wave on bit 1
        words = [(1 if (i // 50) % 2 == 0 else 0) << args.bit for i in range(2000)]
        bits = extract_bit(words, args.bit)
        edges = count_edges(bits)
        print(f"DRY-RUN: edges={edges} samples={len(words)}")
        return 0 if edges >= args.min_edges else 2

    base_url = f"{args.scheme}://{args.host}:{args.port}"
    auth = HTTPBasicAuth(args.user, args.password)

    sample_rate = args.sample_rate or choose_sample_rate(args.window_s)

    if not args.verify_ssl:
        print("Warning: SSL verification disabled.")

    channels = ["disabled"] * 16

    try:
        configure_la(
            base_url,
            auth,
            args.verify_ssl,
            sample_rate,
            trigger_enabled=False,
            trigger_position=50,
            trigger_mode_or=True,
            capture_internal_test_signal=args.internal_test,
            channels=channels,
        )
    except Exception as exc:
        print(f"ERROR: configure failed ({exc})")
        print("Hint: No network/auth or webserver unreachable.")
        return 2

    try:
        if args.mode == "instant":
            blob = instant_capture(base_url, auth, args.verify_ssl)
        else:
            blob = triggered_capture(base_url, auth, args.verify_ssl, timeout_s=args.timeout)
    except Exception as exc:
        print(f"ERROR: capture failed ({exc})")
        return 3

    if len(blob) < 10:
        print("ERROR: Capture returned too few bytes")
        return 4

    words = parse_samples(blob)
    if not words:
        print("ERROR: No samples decoded")
        return 4

    window_s = len(words) / float(sample_rate)

    if args.scan:
        counts = edge_counts_all_bits(words)
        print(f"sampleRate={sample_rate}Hz samples={len(words)} window={window_s:.6f}s")
        print("edge_counts:")
        for i, c in enumerate(counts):
            print(f"  bit{i}: {c}")
        # if scanning only, use max count as signal of activity
        if max(counts) == 0:
            print("FAIL: No toggling detected on any bit.")
            return 5
        return 0

    if args.bit < 0 or args.bit > 15:
        print("ERROR: --bit must be 0..15")
        return 2

    bits = extract_bit(words, args.bit)
    edges = count_edges(bits)
    high = bits.count(1)
    low = bits.count(0)

    print(f"sampleRate={sample_rate}Hz samples={len(words)} window={window_s:.6f}s")
    print(f"bit={args.bit} edges={edges} high={high} low={low}")

    if edges == 0:
        print("FAIL: Bit never changes (stuck high/low).")
        return 6
    if edges < args.min_edges:
        print("FAIL: Only 1 edge or too few edges.")
        print("Hint: lower sample rate or speed up blink.")
        return 7

    print("PASS: Toggling detected")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="admin")
    ap.add_argument("--scheme", default="https", choices=["http", "https"])
    ap.add_argument("--port", type=int, default=443)
    ap.add_argument("--verify-ssl", action="store_true", help="Enable SSL certificate verification")
    ap.add_argument("--mode", default="instant", choices=["instant", "trigger"]) 
    ap.add_argument("--sample-rate", type=int, default=0)
    ap.add_argument("--window-s", type=float, default=0.2, help="Desired window seconds")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--bit", type=int, default=1)
    ap.add_argument("--line", default="", help="PA0..PD3 or P0.1; overrides --bit")
    ap.add_argument("--min-edges", type=int, default=4)
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--internal-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()
    if args.line:
        p = args.line.strip().upper()
        if len(p) == 3 and p[0] == "P" and p[1] in ("A", "B", "C", "D") and p[2].isdigit():
            idx = int(p[2])
            if 0 <= idx <= 3:
                base = {"A": 0, "B": 4, "C": 8, "D": 12}[p[1]]
                args.bit = base + idx
        elif "." in p and p.split(".")[-1].isdigit():
            args.bit = int(p.split(".")[-1])
    if args.sample_rate and args.sample_rate not in SUPPORTED_RATES:
        print("Warning: sample-rate not in supported list, device will pick nearest.")

    code = run(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
