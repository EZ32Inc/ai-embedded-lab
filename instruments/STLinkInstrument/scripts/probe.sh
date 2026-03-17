#!/usr/bin/env bash
# Probe connected ST-Link devices and print target info.
# Usage: probe.sh [--st-info-path /path/to/st-info]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_ST_INFO="$INSTRUMENT_DIR/upstream/stlink/build/bin/st-info"

ST_INFO="${ST_INFO_PATH:-$DEFAULT_ST_INFO}"

# Fall back to system-installed st-info
if [[ ! -x "$ST_INFO" ]]; then
    ST_INFO="$(command -v st-info 2>/dev/null || true)"
fi

if [[ -z "$ST_INFO" || ! -x "$ST_INFO" ]]; then
    echo "[probe] ERROR: st-info not found. Run scripts/build.sh first."
    exit 1
fi

echo "[probe] Using: $ST_INFO"
echo "[probe] Probing..."
"$ST_INFO" --probe
