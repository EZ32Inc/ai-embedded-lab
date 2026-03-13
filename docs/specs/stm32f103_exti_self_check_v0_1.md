# STM32F103 EXTI Self-Check v0.1

## Purpose
- Add one bounded EXTI execution proof on the unified `stm32f103` capability fixture.
- Reuse the existing `PA8 -> PB8` loopback wiring and `PA4 -> P0.0` external proof path.

## Pins
- `PA8 = EXTI source`
- `PB8 = EXTI input`
- `PA8 -> PB8` manual loopback
- `PA4 -> P0.0` external machine-checkable result
- Optional auxiliary observe remains `PA5 -> P0.1`, but it is not part of the pass/fail contract.

## Method
- Firmware drives repeated edges on `PA8`.
- Firmware enables EXTI on `PB8` for both rising and falling edges and counts/qualifies those interrupts over bounded windows.
- If EXTI activity is good, firmware exports a stable pass waveform on `PA4`.
- If EXTI activity is bad, firmware keeps `PA4` low.

## Success criteria
- One real hardware run passes.
- `PA4` shows the expected bounded pass waveform.
- The result is captured as a bounded EXTI self-check proof on the STM32 anchor.

## Likely failure modes
- Missing `PA8 -> PB8` loopback
- Incorrect EXTI routing for line 8 to Port B
- EXTI interrupt not enabled
- `PB8` never sees both rising and falling events
- `PA4` pass/fail export logic misconfigured

## Regression framing
- Change class: `Class 3` bounded path-specific runtime change
- Affected anchor: `stm32f103` primary sample-board capability anchor
- Minimum regression tier: `Tier 4`

## Validation commands
```bash
python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/stm32f103_exti_banner.json
python3 -m ael explain-stage --board stm32f103 --test tests/plans/stm32f103_exti_banner.json --stage plan
python3 -m ael run --board stm32f103 --test tests/plans/stm32f103_exti_banner.json
```
