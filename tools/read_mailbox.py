#!/usr/bin/env python3
"""
AEL Debug Mailbox Reader — STM32G431CBU6 proof-of-concept

Attaches to the target via existing BMDA GDB endpoint, reads the 16-byte
mailbox struct from a fixed RAM address, and prints the result.

Usage:
    python3 tools/read_mailbox.py
    python3 tools/read_mailbox.py --ip 192.168.2.62 --addr 0x20007F00

Expected output (pass firmware):
    magic      : 0xae100001  OK
    status     : 0x00000002  PASS
    error_code : 0x00000000
    detail0    : 0x00000000
"""

import argparse
import re
import subprocess
import sys

MAILBOX_MAGIC = 0xAE100001

STATUS_NAMES = {
    0: "EMPTY",
    1: "RUNNING",
    2: "PASS",
    3: "FAIL",
}


def read_mailbox(gdb_endpoint: str, target_id: int, addr: int) -> dict:
    """
    Attach to target via GDB batch, read 4 words from addr, return parsed dict.
    """
    cmds = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {gdb_endpoint}",
        "monitor a",
        f"attach {target_id}",
        f"x/4xw {addr:#010x}",
        "detach",
        "quit",
    ]
    gdb_args = ["arm-none-eabi-gdb", "--batch"] + [
        item for cmd in cmds for item in ("-ex", cmd)
    ]

    try:
        result = subprocess.run(
            gdb_args, capture_output=True, text=True, timeout=20
        )
    except subprocess.TimeoutExpired:
        print("ERROR: GDB timed out", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: arm-none-eabi-gdb not found", file=sys.stderr)
        sys.exit(1)

    # Parse hex words from GDB memory dump output
    # Example line: "0x20007f00:\t0xae100001\t0x00000002\t0x00000000\t0x00000000"
    words = []
    for line in result.stdout.splitlines():
        if f"{addr:#010x}" in line.lower():
            found = re.findall(r"0x[0-9a-fA-F]+", line)
            # first match is the address itself — skip it
            words = [int(x, 16) for x in found[1:]]
            break

    if len(words) < 4:
        print(f"ERROR: could not parse mailbox from GDB output.", file=sys.stderr)
        print("GDB stdout:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print("GDB stderr:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    return {
        "magic":      words[0],
        "status":     words[1],
        "error_code": words[2],
        "detail0":    words[3],
        "raw_stdout": result.stdout,
    }


def main():
    ap = argparse.ArgumentParser(description="Read AEL debug mailbox from target RAM")
    ap.add_argument("--ip",        default="192.168.2.62")
    ap.add_argument("--port",      type=int, default=4242)
    ap.add_argument("--target-id", type=int, default=1)
    ap.add_argument("--addr",      default="0x20007F00")
    ap.add_argument("--verbose",   action="store_true")
    args = ap.parse_args()

    addr     = int(args.addr, 16)
    endpoint = f"{args.ip}:{args.port}"

    print(f"Reading mailbox from {endpoint} target={args.target_id} addr={addr:#010x}")
    mb = read_mailbox(endpoint, args.target_id, addr)

    if args.verbose:
        print("\nRaw GDB output:")
        print(mb["raw_stdout"])

    print()
    magic_ok = mb["magic"] == MAILBOX_MAGIC
    status_name = STATUS_NAMES.get(mb["status"], f"UNKNOWN({mb['status']})")

    print(f"  magic      : {mb['magic']:#010x}  {'OK' if magic_ok else 'BAD — unexpected magic'}")
    print(f"  status     : {mb['status']:#010x}  {status_name}")
    print(f"  error_code : {mb['error_code']:#010x}")
    print(f"  detail0    : {mb['detail0']:#010x}")

    if not magic_ok:
        print("\nFAIL: magic mismatch — mailbox not written or wrong address")
        sys.exit(1)

    if mb["status"] == 2:   # STATUS_PASS
        print("\nResult: PASS")
        sys.exit(0)
    elif mb["status"] == 3:  # STATUS_FAIL
        print(f"\nResult: FAIL  error_code={mb['error_code']:#010x}  detail0={mb['detail0']:#010x}")
        sys.exit(1)
    elif mb["status"] == 1:  # STATUS_RUNNING
        print("\nResult: RUNNING — DUT has not finished yet")
        sys.exit(1)
    else:
        print(f"\nResult: UNKNOWN status={mb['status']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
