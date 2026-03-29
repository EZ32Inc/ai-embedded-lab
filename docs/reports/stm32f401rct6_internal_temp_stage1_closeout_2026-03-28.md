# STM32F401RCT6 Internal Temperature Stage 1 Closeout

**Date:** 2026-03-28
**Board:** `stm32f401rct6`
**Test:** `tests/plans/stm32f401rct6_internal_temp_mailbox.json`
**Pack coverage:** `packs/stm32f401rct6_stage1.json`

## Outcome

The STM32F401RCT6 Rule-B Stage 1 internal peripheral self-test now includes an
ADC-based internal temperature mailbox test and it has been live-validated on the
current ESP32JTAG bench.

Validated run:
- `2026-03-28_21-11-04_stm32f401rct6_stm32f401rct6_internal_temp_mailbox`

Result:
- `PASS`

## What Was Added

- New firmware target:
  - `firmware/targets/stm32f401rct6_internal_temp_mailbox/`
- New test plan:
  - `tests/plans/stm32f401rct6_internal_temp_mailbox.json`
- Stage 1 pack updated:
  - `packs/stm32f401rct6_stage1.json`
- Board note updated:
  - `docs/boards/stm32f401rct6.md`

## Proof Model

This is a no-wire mailbox self-test using:
- `ADC1`
- internal temperature sensor channel `18`
- `ADC_CCR.TSVREFE`
- long sample time on channel 18

PASS criteria:
- average of 8 samples is non-zero
- average is not saturated
- spread across samples is non-zero

Mailbox detail:
- `detail0 = (spread << 16) | average`

## Why This Is A Good Stage 1 Test

It proves more than Stage 0:
- internal ADC path is alive
- internal sensor mux is alive
- temperature-sensor enable path is alive
- conversion sequencing and mailbox reporting work

And it still requires:
- no extra wiring
- no UART
- no external analog stimulus

## Bench Context

- Instrument: `esp32jtag_blackpill_192_168_2_106`
- Endpoint: `192.168.2.106:4242`
- Flash path: preserved historical BMDA second-attach sequence

## Resulting Stage 1 Structure

`STM32F401RCT6` Stage 1 now contains:
- `tests/plans/stm32f401rct6_timer_mailbox.json`
- `tests/plans/stm32f401rct6_internal_temp_mailbox.json`

Both are no-wire mailbox self-tests.
