#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    index: int
    label: str
    port: int
    expect: str


CHANNELS = [
    Channel(0, "S1/socket", 4242, "absent"),
    Channel(1, "S2/socket", 4243, "absent"),
    Channel(2, "S3/socket", 4244, "absent"),
    Channel(3, "S4/socket", 4245, "absent"),
    Channel(4, "STM32H503", 4246, "STM32H5"),
    Channel(5, "V305", 4247, "CH32V"),
    Channel(6, "RP2350", 4248, "RP2350"),
    Channel(7, "CH32V006", 4249, "CH32V"),
]


def _tcp_open(host: str, port: int, timeout_s: float) -> tuple[bool, str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_s)
    try:
        sock.connect((host, port))
        return True, ""
    except OSError as exc:
        return False, str(exc)
    finally:
        sock.close()


def _run_gdb_scan(gdb: str, host: str, port: int, frequency: int, timeout_s: float) -> tuple[str, int | None]:
    cmd = [
        gdb,
        "-q",
        "--nx",
        "--batch",
        "-ex",
        f"target extended-remote {host}:{port}",
        "-ex",
        f"monitor frequency {frequency}",
        "-ex",
        "monitor swd_scan",
        "-ex",
        "detach",
        "-ex",
        "quit",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        out = ((exc.stdout or "") + (exc.stderr or "")).strip()
        return (out + "\nTIMEOUT").strip(), None
    return ((res.stdout or "") + (res.stderr or "")).strip(), int(res.returncode)


def _classify_scan(output: str) -> tuple[bool, str]:
    text = output.replace("\x00", "")
    if "Available Targets:" in text and "No. Att Driver" in text:
        drivers = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("1 ") or line.startswith("2 "):
                parts = line.split()
                if len(parts) >= 2:
                    drivers.append(" ".join(parts[1:]))
        return True, "; ".join(drivers) if drivers else "target-present"
    if "SWD scan failed" in text or "Failed" in text:
        return False, "swd-scan-failed"
    if "Target voltage:" in text:
        return False, "no-target-listed"
    return False, "unknown"


def _expected_ok(expect: str, present: bool, summary: str) -> bool:
    if expect == "absent":
        return not present
    return present and expect.lower() in summary.lower()


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan CoreWeaver S3JTAG8CH GDB ports and SWD targets.")
    ap.add_argument("--host", default="192.168.4.1")
    ap.add_argument("--gdb", default="arm-none-eabi-gdb")
    ap.add_argument("--frequency", type=int, default=100000)
    ap.add_argument("--tcp-timeout", type=float, default=1.0)
    ap.add_argument("--gdb-timeout", type=float, default=12.0)
    ap.add_argument("--json", action="store_true", help="Print JSON result in addition to status lines.")
    args = ap.parse_args()

    gdb_path = shutil.which(args.gdb)
    if not gdb_path:
        print(f"[COREWEAVER_SCAN] FAIL: gdb not found: {args.gdb}")
        return 2

    results = []
    failures = 0

    print(f"[COREWEAVER_SCAN] host={args.host} gdb={gdb_path} frequency={args.frequency}")
    for ch in CHANNELS:
        tcp_ok, tcp_error = _tcp_open(args.host, ch.port, args.tcp_timeout)
        output = ""
        present = False
        summary = "tcp-closed"
        rc = None
        if tcp_ok:
            output, rc = _run_gdb_scan(gdb_path, args.host, ch.port, args.frequency, args.gdb_timeout)
            present, summary = _classify_scan(output)
        else:
            summary = tcp_error or "tcp-closed"

        ok = tcp_ok and _expected_ok(ch.expect, present, summary)
        if not ok:
            failures += 1
        status = "OK" if ok else "FAIL"
        print(
            f"[COREWEAVER_SCAN] {status}: ch{ch.index} port={ch.port} "
            f"{ch.label} expect={ch.expect} observed={summary}"
        )
        results.append(
            {
                "channel": ch.index,
                "label": ch.label,
                "port": ch.port,
                "expect": ch.expect,
                "tcp_open": tcp_ok,
                "present": present,
                "summary": summary,
                "returncode": rc,
                "ok": ok,
                "output": output,
            }
        )

    payload = {"host": args.host, "frequency": args.frequency, "ok": failures == 0, "results": results}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if failures:
        print(f"[COREWEAVER_SCAN] FAIL: {failures} channel(s) did not match expectations")
        return 1
    print("[COREWEAVER_SCAN] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
