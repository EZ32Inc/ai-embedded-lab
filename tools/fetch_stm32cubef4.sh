#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$ROOT_DIR/third_party/cache"
DEST_DIR="$CACHE_DIR/STM32CubeF4"
REMOTE_URL="https://github.com/STMicroelectronics/STM32CubeF4.git"

mkdir -p "$CACHE_DIR"

if [[ ! -d "$DEST_DIR/.git" ]]; then
  git clone --recursive "$REMOTE_URL" "$DEST_DIR"
else
  git -C "$DEST_DIR" fetch --tags origin
  git -C "$DEST_DIR" submodule update --init --recursive
fi

echo "repo=$REMOTE_URL"
echo "path=$DEST_DIR"
echo "commit=$(git -C "$DEST_DIR" rev-parse HEAD)"
echo "describe=$(git -C "$DEST_DIR" describe --tags --always)"
