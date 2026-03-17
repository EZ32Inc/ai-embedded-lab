#!/usr/bin/env bash
# Start an ST-Link GDB server (st-util) for a connected STM32 target.
# Usage: gdb_server.sh [--port 4242] [--multi]
# Environment overrides:
#   ST_UTIL_PATH    path to st-util binary
#   GDB_PORT        GDB server listen port (default: 4242)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_ST_UTIL="$INSTRUMENT_DIR/install/bin/st-util"
export LD_LIBRARY_PATH="$INSTRUMENT_DIR/install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

ST_UTIL="${ST_UTIL_PATH:-$DEFAULT_ST_UTIL}"

# Fall back to system-installed st-util
if [[ ! -x "$ST_UTIL" ]]; then
    ST_UTIL="$(command -v st-util 2>/dev/null || true)"
fi

if [[ -z "$ST_UTIL" || ! -x "$ST_UTIL" ]]; then
    echo "[gdb_server] ERROR: st-util not found. Run scripts/build.sh first."
    exit 1
fi

PORT="${GDB_PORT:-4242}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port|-p) PORT="$2"; shift 2 ;;
        --multi) EXTRA_ARGS+=("--multi"); shift ;;
        *) echo "[gdb_server] Unknown argument: $1"; exit 1 ;;
    esac
done

echo "[gdb_server] Using: $ST_UTIL"
echo "[gdb_server] Listening on port: $PORT"
exec "$ST_UTIL" "${EXTRA_ARGS[@]}"   # st-util 1.8.x listens on 4242 by default
