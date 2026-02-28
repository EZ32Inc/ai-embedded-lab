#!/usr/bin/env bash
set -euo pipefail

ELF_DEFAULT="/nvme1t/work/codex/ai-embedded-lab/artifacts/build_stm32/stm32f103_app.elf"
GDB_DEFAULT="arm-none-eabi-gdb"
TARGET_DEFAULT="192.168.4.1:4242"
TARGET_ID_DEFAULT="1"

ELF="${1:-$ELF_DEFAULT}"
GDB_CMD="${GDB_CMD:-$GDB_DEFAULT}"
TARGET="${TARGET:-$TARGET_DEFAULT}"
TARGET_ID="${TARGET_ID:-$TARGET_ID_DEFAULT}"

if [[ ! -f "$ELF" ]]; then
  echo "ELF not found: $ELF" >&2
  exit 2
fi

echo "Flashing STM32 via ESP32JTAG"
echo "  ELF: $ELF"
echo "  Target: $TARGET"
echo "  Target ID: $TARGET_ID"
echo "  GDB: $GDB_CMD"

"$GDB_CMD" -q --nx --batch \
  -ex "target extended-remote $TARGET" \
  -ex "file $ELF" \
  -ex "monitor a" \
  -ex "attach $TARGET_ID" \
  -ex "load" \
  -ex "detach"

echo "Done. If the MCU does not run, power-cycle the board." 
