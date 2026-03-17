#!/usr/bin/env bash
# STLinkInstrument doctor — checks setup health before use.
# Exits 0 if all required checks pass, 1 if any fail.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
STLINK_SRC="$INSTRUMENT_DIR/upstream/stlink"
BUILD_BIN="$STLINK_SRC/build/bin"

PASS=0
FAIL=0

check() {
    local label="$1"
    local ok="$2"
    local detail="${3:-}"
    if [[ "$ok" == "1" ]]; then
        echo "  [OK]   $label${detail:+  ($detail)}"
        ((PASS++)) || true
    else
        echo "  [FAIL] $label${detail:+  ($detail)}"
        ((FAIL++)) || true
    fi
}

echo "=== STLinkInstrument Doctor ==="
echo ""

# 1. Submodule present
if [[ -f "$STLINK_SRC/CMakeLists.txt" ]]; then
    check "Submodule present" 1 "$STLINK_SRC"
else
    check "Submodule present" 0 "run: git submodule update --init --recursive"
fi

# 2. cmake available
if command -v cmake &>/dev/null; then
    CMAKE_VER="$(cmake --version 2>&1 | head -1)"
    check "cmake available" 1 "$CMAKE_VER"
else
    check "cmake available" 0 "install cmake"
fi

# 3. Build artifacts exist
for BIN in st-flash st-info st-util; do
    if [[ -x "$BUILD_BIN/$BIN" ]]; then
        check "Built: $BIN" 1 "$BUILD_BIN/$BIN"
    else
        SYSTEM_BIN="$(command -v "$BIN" 2>/dev/null || true)"
        if [[ -n "$SYSTEM_BIN" ]]; then
            check "Built: $BIN" 1 "system fallback: $SYSTEM_BIN"
        else
            check "Built: $BIN" 0 "run scripts/build.sh"
        fi
    fi
done

# 4. USB device check (ST-Link shows up as USB device)
if command -v lsusb &>/dev/null; then
    STLINK_USB="$(lsusb 2>/dev/null | grep -i "0483:37" || true)"
    if [[ -n "$STLINK_USB" ]]; then
        check "ST-Link USB device" 1 "$STLINK_USB"
    else
        check "ST-Link USB device" 0 "no ST-Link detected (VID 0483:37xx) — is it plugged in?"
    fi
else
    check "ST-Link USB device" 0 "lsusb not available — skipping USB check"
fi

# 5. Probe attempt (only if st-info available)
ST_INFO_BIN="$BUILD_BIN/st-info"
if [[ ! -x "$ST_INFO_BIN" ]]; then
    ST_INFO_BIN="$(command -v st-info 2>/dev/null || true)"
fi

if [[ -n "$ST_INFO_BIN" && -x "$ST_INFO_BIN" ]]; then
    PROBE_OUT="$("$ST_INFO_BIN" --probe 2>&1 || true)"
    if echo "$PROBE_OUT" | grep -qi "Found\|serial\|chipid\|hla-serial"; then
        check "Probe (st-info --probe)" 1 "target detected"
    else
        check "Probe (st-info --probe)" 0 "no target found — check wiring and USB"
    fi
else
    check "Probe (st-info --probe)" 0 "st-info not available — skipping probe check"
fi

echo ""
echo "Result: $PASS OK, $FAIL FAIL"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
