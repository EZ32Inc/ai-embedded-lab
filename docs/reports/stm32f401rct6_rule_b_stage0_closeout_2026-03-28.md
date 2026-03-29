# STM32F401RCT6 Rule-B Stage 0 Closeout

**Date:** 2026-03-28
**Board:** `stm32f401rct6`
**Pack:** `packs/stm32f401rct6_stage0.json`
**Test:** `tests/plans/stm32f401rct6_pc13_blinky_visual.json`

## Outcome

Rule-B suite bootstrap for STM32F401RCT6 is now started and live-validated on the
current ESP32JTAG bench without disturbing the preserved legacy pack.

Validated run:
- `2026-03-28_20-51-46_stm32f401rct6_stm32f401rct6_pc13_blinky_visual`

Result:
- `PASS`

## What Was Added

- New Rule-B Stage 0 truth-layer test:
  - `tests/plans/stm32f401rct6_pc13_blinky_visual.json`
- New Rule-B Stage 0 pack:
  - `packs/stm32f401rct6_stage0.json`
- Board note update:
  - `docs/boards/stm32f401rct6.md`

## Legacy And Rule-B Relationship

The preserved pre-Rule-B pack remains:
- `packs/smoke_stm32f401.json`

Status:
- preserved legacy golden pack
- still expected to pass `8 / 8`
- not replaced by the new Rule-B path

Rule-B status after this closeout:
- Stage 0 exists
- Stage 0 is validated
- later Stage 1 / Stage 2 work should be added in parallel

## Important Implementation Detail

The first attempt reused the older LED-plan shape and failed at verify time because
the generic verify path treated `LED` like a logic-analyzer input.

The correct Rule-B Stage 0 shape for this board is:
- `schema_version: 1.0`
- `test_kind: program_only`
- visual-only bench note
- no generic LA verify stage

That matches the intended role of Stage 0:
- prove flash and runtime on real hardware
- keep the first truth-layer baseline minimal

## Bench Context

- Instrument: `esp32jtag_blackpill_192_168_2_106`
- Endpoint: `192.168.2.106:4242`
- MCU: `STM32F401RCT6`
- LED net: `PC13`
- Flash sequence: preserved historical BMDA second-attach sequence

## Conclusion

STM32F401RCT6 now has two valid suite layers:
- preserved legacy pack: `packs/smoke_stm32f401.json`
- new Rule-B bootstrap pack: `packs/stm32f401rct6_stage0.json`

This is the intended migration pattern: preserve the proven older suite, and build
the newer Rule-B suite beside it stage by stage.
