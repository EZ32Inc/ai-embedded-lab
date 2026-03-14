#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: tools/run_live_bench.sh <command> [args...]" >&2
  echo "example: tools/run_live_bench.sh python3 -m ael verify-default run" >&2
  exit 2
fi

echo "LIVE_BENCH: running with real bench intent."
echo "LIVE_BENCH: sandbox trial runs are invalid for this command class."
echo "LIVE_BENCH: command: $*"
exec "$@"
