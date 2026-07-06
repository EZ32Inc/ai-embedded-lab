#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


CHANNEL_PORTS = {
    0: 4242,
    1: 4243,
    2: 4244,
    3: 4245,
    4: 4246,
    5: 4247,
    6: 4248,
    7: 4249,
}


def _commands(args: argparse.Namespace) -> list[str]:
    cmds = [
        f"target extended-remote {args.host}:{args.port}",
        f"monitor frequency {args.frequency}",
    ]
    if args.connect_reset:
        cmds.append("monitor connect_rst enable")
    cmds.extend(
        [
            "monitor swd_scan",
            f"file {args.elf}",
            f"attach {args.target_id}",
            "load",
        ]
    )
    if args.compare_sections:
        cmds.append("compare-sections")
    cmds.extend(
        [
            f"attach {args.target_id}",
            "detach",
            "quit",
        ]
    )
    return cmds


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Flash an ARM Cortex target through CoreWeaver S3JTAG8CH without "
            "using monitor reset/run after load."
        )
    )
    parser.add_argument("elf", help="ELF file to flash")
    parser.add_argument("--host", default="192.168.4.1")
    parser.add_argument("--channel", type=int, choices=sorted(CHANNEL_PORTS), required=True)
    parser.add_argument("--port", type=int, default=0, help="Override GDB port")
    parser.add_argument("--target-id", type=int, default=1)
    parser.add_argument("--frequency", type=int, default=100000)
    parser.add_argument("--connect-reset", action="store_true")
    parser.add_argument("--no-compare-sections", dest="compare_sections", action="store_false")
    parser.add_argument("--gdb", default="arm-none-eabi-gdb")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    elf = Path(args.elf)
    if not elf.exists():
        print(f"ELF not found: {elf}", file=sys.stderr)
        return 2

    args.port = int(args.port or CHANNEL_PORTS[args.channel])
    cmd = [args.gdb, "-q", "--nx", "--batch"]
    for gdb_cmd in _commands(args):
        cmd.extend(["-ex", gdb_cmd])

    print(" ".join(cmd))
    result = subprocess.run(cmd, text=True, timeout=max(1.0, args.timeout))
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
