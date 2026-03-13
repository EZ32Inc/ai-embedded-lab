# STM32F103 EXTI Self-Check Closeout v0.1

## Path
- Board: `stm32f103`
- Test: `tests/plans/stm32f103_exti_banner.json`
- Firmware: `firmware/targets/stm32f103_exti`
- Control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`

## Fixture
- External observe: `PA4 -> P0.0`
- Optional auxiliary observe: `PA5 -> P0.1`
- Internal EXTI loopback: `PA8 -> PB8`

## Success method
Firmware generates repeated edges on `PA8`, receives them on `PB8` through the loopback, counts EXTI events internally, and exports the bounded pass/fail result on `PA4`. AEL verifies `PA4` through the existing STM32 external observe path.

## Real result
- Run: `2026-03-13_11-27-03_stm32f103_stm32f103_exti_banner`
- Result: `PASS`
- Verify summary:
  - `edges=25`
  - `high=32363`
  - `low=33169`

## What this proves
- The `PA8 -> PB8` loopback works as a bounded EXTI self-check path on the unified STM32 fixture.
- EXTI success can be encoded back onto `PA4` and verified automatically by AEL.
- The STM32 capability anchor now has a bounded live-pass proof for EXTI.

## What this does not prove
- General interrupt framework completeness
- Timer capture/timing correctness
- Broad multi-board EXTI portability
