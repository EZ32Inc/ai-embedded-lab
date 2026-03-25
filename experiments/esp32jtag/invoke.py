#!/usr/bin/env python3
"""
ESP32JTAG Capability Invoker
============================
Standalone entry point: resolve a named capability and run it.

This is a thin wrapper around ael.board.capability_registry that does not
require the full AEL CLI. Useful for quick direct invocation.

Usage
-----
  # List all capabilities
  python experiments/esp32jtag/invoke.py --list

  # Run by natural name (case-insensitive, keyword matching)
  python experiments/esp32jtag/invoke.py "port d loopback self-test"
  python experiments/esp32jtag/invoke.py "loopback"
  python experiments/esp32jtag/invoke.py "firmware smoke"

  # Verbose output
  python experiments/esp32jtag/invoke.py --verbose "port d loopback"

  # Via AEL CLI (equivalent)
  ael invoke "port d loopback self-test"
  ael invoke --list

Exit codes
----------
  0  — capability ran and passed (or API info printed)
  1  — capability ran and failed, or capability not found
  2  — capability not found
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ael.board.capability_registry import load_registry

BOARD_ID = "esp32jtag_instrument_s3"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ESP32JTAG capability invoker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "capability", nargs="?", default=None,
        help="Capability name or alias (e.g. \"port d loopback self-test\")",
    )
    parser.add_argument(
        "--list", dest="do_list", action="store_true",
        help="List all available capabilities",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output (passed to capability script if applicable)",
    )
    args = parser.parse_args()

    reg = load_registry(BOARD_ID, repo_root=_REPO)

    if args.do_list:
        print(reg.list_capabilities(verbose=args.verbose))
        return 0

    if not args.capability:
        print("Provide a capability name/alias, or use --list to see all capabilities.")
        print(f"\nExample: python {Path(__file__).name} \"port d loopback self-test\"")
        return 1

    return reg.invoke(args.capability, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
