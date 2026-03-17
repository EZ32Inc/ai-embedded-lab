#!/usr/bin/env bash
# Flash a firmware binary to an STM32 target via ST-Link.
# Usage: flash.sh <firmware.bin> [--addr 0x08000000] [--reset]
# Environment overrides:
#   ST_FLASH_PATH   path to st-flash binary
#   FLASH_ADDR      flash start address (default: 0x08000000)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_ST_FLASH="$INSTRUMENT_DIR/install/bin/st-flash"
export LD_LIBRARY_PATH="$INSTRUMENT_DIR/install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

ST_FLASH="${ST_FLASH_PATH:-$DEFAULT_ST_FLASH}"

# Fall back to system-installed st-flash
if [[ ! -x "$ST_FLASH" ]]; then
    ST_FLASH="$(command -v st-flash 2>/dev/null || true)"
fi

if [[ -z "$ST_FLASH" || ! -x "$ST_FLASH" ]]; then
    echo "[flash] ERROR: st-flash not found. Run scripts/build.sh first."
    exit 1
fi

if [[ $# -lt 1 ]]; then
    echo "Usage: flash.sh <firmware.bin> [--addr 0x08000000] [--reset]"
    exit 1
fi

FIRMWARE="$1"
shift

ADDR="${FLASH_ADDR:-0x08000000}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --addr) ADDR="$2"; shift 2 ;;
        --reset) EXTRA_ARGS+=("--reset"); shift ;;
        *) echo "[flash] Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ ! -f "$FIRMWARE" ]]; then
    echo "[flash] ERROR: firmware file not found: $FIRMWARE"
    exit 1
fi

echo "[flash] Using: $ST_FLASH"
echo "[flash] Firmware: $FIRMWARE"
echo "[flash] Address: $ADDR"
"$ST_FLASH" "${EXTRA_ARGS[@]}" write "$FIRMWARE" "$ADDR"
