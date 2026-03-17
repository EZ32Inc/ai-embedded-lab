#!/usr/bin/env bash
# Build st-flash, st-info, st-util from the EZ32Inc/stlink fork.
# Output binaries land in: upstream/stlink/build/bin/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUMENT_DIR="$(dirname "$SCRIPT_DIR")"
STLINK_SRC="$INSTRUMENT_DIR/upstream/stlink"
BUILD_DIR="$STLINK_SRC/build"
INSTALL_PREFIX="$INSTRUMENT_DIR/install"

if [[ ! -f "$STLINK_SRC/CMakeLists.txt" ]]; then
    echo "[build] ERROR: submodule not initialised — run: git submodule update --init --recursive"
    exit 1
fi

echo "[build] Configuring stlink (prefix: $INSTALL_PREFIX)..."
cmake -S "$STLINK_SRC" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DBUILD_TESTING=OFF \
    2>&1

echo "[build] Building..."
cmake --build "$BUILD_DIR" --parallel "$(nproc)" 2>&1

echo "[build] Installing to $INSTALL_PREFIX (no sudo required)..."
# Install all components except system-level modprobe.d/udev (those need sudo separately)
cmake --install "$BUILD_DIR" --component runtime 2>&1 || true
cmake --install "$BUILD_DIR" --component library 2>&1 || true

# Chip configs: install manually to avoid modprobe.d permission failure
mkdir -p "$INSTALL_PREFIX/share/stlink/config/chips"
cp "$STLINK_SRC/config/chips/"*.chip "$INSTALL_PREFIX/share/stlink/config/chips/"

echo "[build] Done. Binaries in $INSTALL_PREFIX/bin/:"
ls "$INSTALL_PREFIX/bin/" 2>/dev/null || ls "$BUILD_DIR/bin/"
