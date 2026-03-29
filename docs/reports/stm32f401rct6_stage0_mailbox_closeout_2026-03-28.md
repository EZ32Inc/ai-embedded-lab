# STM32F401RCT6 Stage 0 Mailbox Closeout

**Date:** 2026-03-28
**Board:** `stm32f401rct6`
**Pack:** `packs/stm32f401rct6_stage0_mailbox.json`
**Test:** `tests/plans/stm32f401rct6_minimal_runtime_mailbox.json`

## Outcome

A separate mailbox-based Rule-B Stage 0 baseline now exists for STM32F401RCT6 and
has been live-validated on the current ESP32JTAG bench.

Validated run:
- `2026-03-28_21-00-20_stm32f401rct6_stm32f401rct6_minimal_runtime_mailbox`

Result:
- `PASS`

## What Was Added

- New firmware target:
  - `firmware/targets/stm32f401rct6_minimal_runtime_mailbox/`
- New mailbox plan:
  - `tests/plans/stm32f401rct6_minimal_runtime_mailbox.json`
- New separate Stage 0 mailbox pack:
  - `packs/stm32f401rct6_stage0_mailbox.json`
- Board note update:
  - `docs/boards/stm32f401rct6.md`

## Proof Model

This Stage 0 path uses:
- `test_kind: baremetal_mailbox`
- no extra wiring beyond SWD and ground
- mailbox status as the formal proof
- `PC13` LED only as optional visual support

Mailbox behavior:
- firmware writes `RUNNING`
- after a short deterministic settle, firmware writes `PASS`
- `detail0` increments in the idle loop after PASS

## Mailbox Addressing Rule

The mailbox is not placed at a guessed SRAM address.

Instead:
- linker reserves a dedicated mailbox region
- reserved region: `0x2000FC00–0x2000FFFF`
- plan verifies against `0x2000FC00`
- stack top is lowered to the start of the mailbox region

That makes the Stage 0 runtime gate deterministic and keeps the stack out of the
mailbox block.

## Bench Context

- Instrument: `esp32jtag_blackpill_192_168_2_106`
- Endpoint: `192.168.2.106:4242`
- MCU: `STM32F401RCT6`
- Flash path: preserved historical BMDA second-attach sequence

## Resulting Stage 0 Structure

STM32F401RCT6 now has two separate Rule-B Stage 0 assets:
- visual-only baseline:
  - `packs/stm32f401rct6_stage0.json`
- mailbox runtime-gate baseline:
  - `packs/stm32f401rct6_stage0_mailbox.json`

This keeps the proof models separate:
- visual confidence path
- machine-verifiable runtime gate
