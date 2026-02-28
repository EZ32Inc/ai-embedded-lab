import argparse
import os
import sys

from orchestrator import run_cli


def main():
    parser = argparse.ArgumentParser(prog="ael")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--test", required=True)
    run_p.add_argument("--board", required=False, help="Board id (e.g. rp2040_pico)")
    run_p.add_argument("--probe", default=os.path.join("configs", "esp32jtag.yaml"))
    run_p.add_argument("--wiring", required=False)
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    args = parser.parse_args()
    if args.cmd == "run":
        if args.verbose:
            output_mode = "verbose"
        elif args.quiet:
            output_mode = "quiet"
        else:
            output_mode = "normal"
        code = run_cli(
            probe_path=args.probe,
            board_id=args.board,
            test_path=args.test,
            wiring=args.wiring,
            output_mode=output_mode,
        )
        sys.exit(code)


if __name__ == "__main__":
    main()
