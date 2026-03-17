#!/usr/bin/env bash
# Build st-flash, st-info, st-util from the EZ32Inc/stlink fork.
# Output binaries land in: upstream/stlink/build/bin/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
STLINK_SRC="$INSTRUMENT_DIR/upstream/stlink"
BUILD_DIR="$STLINK_SRC/build"

if [[ ! -f "$STLINK_SRC/CMakeLists.txt" ]]; then
    echo "[build] ERROR: submodule not initialised — run: git submodule update --init --recursive"
    exit 1
fi

echo "[build] Configuring stlink..."
cmake -S "$STLINK_SRC" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF \
    2>&1

echo "[build] Building..."
cmake --build "$BUILD_DIR" --parallel "$(nproc)" 2>&1

echo "[build] Done. Binaries:"
ls "$BUILD_DIR/bin/"
