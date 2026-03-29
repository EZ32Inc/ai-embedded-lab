# STM32F401RCT6 Stage 1 Timer Mailbox Closeout

**Date:** 2026-03-28
**Board:** `stm32f401rct6`
**Pack:** `packs/stm32f401rct6_stage1.json`
**Test:** `tests/plans/stm32f401rct6_timer_mailbox.json`

## Outcome

The first Rule-B Stage 1 no-wire self-test for STM32F401RCT6 now exists and has
been live-validated on the current ESP32JTAG bench.

Validated run:
- `2026-03-28_21-04-08_stm32f401rct6_stm32f401rct6_timer_mailbox`

Result:
- `PASS`

## What Was Added

- New Stage 1 firmware target:
  - `firmware/targets/stm32f401rct6_timer_mailbox/`
- New Stage 1 test plan:
  - `tests/plans/stm32f401rct6_timer_mailbox.json`
- New Stage 1 pack:
  - `packs/stm32f401rct6_stage1.json`
- Board note update:
  - `docs/boards/stm32f401rct6.md`

## What This Test Proves

This is a true no-extra-wire self-test beyond Stage 0.

Proof path:
- linker-reserved mailbox at `0x2000FC00`
- TIM3 update interrupt at ~100 ms from 16 MHz HSI
- NVIC interrupt delivery
- PASS after 10 interrupts
- `detail0 = interrupt count`

This exercises:
- APB1 peripheral clock enable
- TIM3 basic timer configuration
- update interrupt generation
- vector table correctness
- NVIC delivery
- WFI resume path

## Failure And Fix

The first implementation failed with:
- mailbox stuck at `RUNNING`

Root cause:
- `TIM3_IRQHandler` was placed at the wrong vector-table index
- external IRQ 29 must be at vector entry `16 + 29`, not at a shortened table tail

Fix:
- expand the startup vector table to include the exception slots and the full IRQ
  numbering up to `TIM3`
- keep `TIM3_IRQHandler` at IRQ 29 explicitly

Commit carrying the fix:
- `6e89a5e` `Fix STM32F401 stage1 timer IRQ vector`

## Resulting Rule-B Structure

STM32F401RCT6 now has:
- Stage 0 visual baseline:
  - `packs/stm32f401rct6_stage0.json`
- Stage 0 mailbox runtime gate:
  - `packs/stm32f401rct6_stage0_mailbox.json`
- Stage 1 no-wire self-test:
  - `packs/stm32f401rct6_stage1.json`

## Bench Context

- Instrument: `esp32jtag_blackpill_192_168_2_106`
- Endpoint: `192.168.2.106:4242`
- Flash path: preserved historical BMDA second-attach sequence
