# STM32F103 Capture/Timing Self-Check Closeout v0.1

## Path
- Board: `stm32f103`
- Test: `stm32f103_capture_banner`
- Firmware target: `firmware/targets/stm32f103_capture`
- Control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`

## Unified fixture assumptions
- External machine-checkable observe path:
  - `PA4 -> P0.0`
- Optional auxiliary observe:
  - `PA5 -> P0.1`
- Preserved loopbacks:
  - `PA1 -> PA0`
  - `PA9 -> PA10`
  - `PA7 -> PA6`
  - `PA8 -> PB8`

## Bounded success method
- Firmware drives a timed signal on `PA8`.
- `PA8` is looped to `PB8`.
- Firmware uses the internal timing/capture path on `PB8` to decide whether capture behavior is good enough.
- Firmware exports pass/fail on `PA4`.
- AEL verifies `PA4` through the normal external observe path.

## Real result
- Run ID:
  - `2026-03-13_11-35-42_stm32f103_stm32f103_capture_banner`
- Result:
  - `PASS`
- Verify summary:
  - `edges=25`
  - `high=33104`
  - `low=32428`
  - `window=0.2520s`

## What this proves
- The unified `PA8 -> PB8` fixture can support a bounded capture/timing self-check on real hardware.
- The firmware-side timing/capture decision can be exported onto `PA4`.
- AEL can verify the resulting external proof signal successfully.

## What this does not prove
- Full timer/capture framework support
- Precise timing metrology
- Any broader multi-board or multi-instrument timing model

## Regression framing
- Change class: `Class 3`
- Affected anchor: `stm32f103` primary sample-board capability anchor
- Minimum regression tier: `Tier 4`

## Recommended interpretation
Treat this as a bounded live-pass proof for the STM32 unified capability fixture.
Do not over-upgrade it into a broad timing framework claim.
