#!/usr/bin/env bash
# Start an ST-Link GDB server (st-util) for a connected STM32 target.
# Usage: gdb_server.sh [--port 4242] [--multi] [--stlink-device BUS:ADDR]
# Environment overrides:
#   ST_UTIL_PATH      path to st-util binary
#   GDB_PORT          GDB server listen port (default: 4242)
#   STLINK_DEVICE     target a specific ST-Link: "BUS:ADDR" (e.g. 001:086)
#                     Can also be set via --stlink-device flag.
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
        --stlink-device)
            # Set STLINK_DEVICE env var so libstlink targets this specific device.
            # Format: BUS:ADDR (e.g. 001:086) — matches lsusb bus/device numbers.
            export STLINK_DEVICE="$2"
            shift 2
            ;;
        *) echo "[gdb_server] Unknown argument: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Multi-device detection: if STLINK_DEVICE is not set, scan sysfs for all
# connected ST-Link devices. Warn and require selection when count > 1.
# ---------------------------------------------------------------------------
_count_stlink_devices() {
    local count=0
    for dev in /sys/bus/usb/devices/*/; do
        local vid pid
        vid=$(cat "${dev}idVendor" 2>/dev/null || true)
        pid=$(cat "${dev}idProduct" 2>/dev/null || true)
        if [[ "$vid" == "0483" && "$pid" == "3748" ]]; then
            count=$((count + 1))
        fi
    done
    echo "$count"
}

_list_stlink_devices() {
    local idx=0
    for dev in /sys/bus/usb/devices/*/; do
        local vid pid
        vid=$(cat "${dev}idVendor" 2>/dev/null || true)
        pid=$(cat "${dev}idProduct" 2>/dev/null || true)
        if [[ "$vid" != "0483" || "$pid" != "3748" ]]; then
            continue
        fi
        local busnum devnum usb_path
        busnum=$(cat "${dev}busnum" 2>/dev/null || echo "?")
        devnum=$(cat "${dev}devnum" 2>/dev/null || echo "?")
        usb_path=$(basename "$dev")
        local serial_hex
        serial_hex=$(cat "${dev}serial" 2>/dev/null | od -A n -t x1 | tr -d ' \n' || true)
        local bus_fmt dev_fmt
        bus_fmt=$(printf "%03d" "$busnum" 2>/dev/null || echo "$busnum")
        dev_fmt=$(printf "%03d" "$devnum" 2>/dev/null || echo "$devnum")
        echo "  [$idx] USB path: $usb_path  →  --stlink-device ${bus_fmt}:${dev_fmt}  (USB ID: ${serial_hex:-n/a})"
        idx=$((idx + 1))
    done
}

if [[ -z "${STLINK_DEVICE:-}" ]]; then
    _n=$(_count_stlink_devices)
    if [[ "$_n" -gt 1 ]]; then
        echo ""
        echo "[gdb_server] ERROR: ${_n} ST-Link devices found but no target specified."
        echo ""
        echo "  Cannot auto-select — ambiguous which device to use."
        echo "  Please re-run with --stlink-device BUS:ADDR:"
        echo ""
        _list_stlink_devices
        echo ""
        echo "  Example:"
        echo "    $0 --stlink-device 001:087 [other options]"
        echo ""
        echo "  Or run:  ael instruments usb-probe  to see full device details."
        exit 1
    elif [[ "$_n" -eq 0 ]]; then
        echo "[gdb_server] WARNING: No ST-Link devices found via sysfs. Proceeding anyway..."
    fi
fi

echo "[gdb_server] Using: $ST_UTIL"
echo "[gdb_server] Listening on port: $PORT"
if [[ -n "${STLINK_DEVICE:-}" ]]; then
    echo "[gdb_server] Targeting ST-Link device: $STLINK_DEVICE"
fi
exec "$ST_UTIL" --listen_port "$PORT" "${EXTRA_ARGS[@]}"
