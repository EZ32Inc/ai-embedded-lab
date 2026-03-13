# STM32F103 PWM Self-Check v0.1

## Purpose
- Add one bounded PWM execution proof on the unified `stm32f103` capability fixture.
- Reuse the existing STM32 control/probe setup without adding a new instrument role.

## Pins
- `PA8 = TIM1_CH1 PWM output`
- `PB8 = PWM self-check input`
- `PA8 -> PB8` manual loopback
- `PA4 -> P0.0` external machine-checkable result
- Optional auxiliary observe remains `PA5 -> P0.1`, but it is not part of the pass/fail contract.

## Method
- Firmware generates a fixed-frequency PWM waveform on `PA8`.
- Firmware samples `PB8` over bounded windows and confirms that both high and low states are observed.
- If the PWM self-check is good, firmware exports a stable pass waveform on `PA4`.
- If the PWM self-check is bad, firmware keeps `PA4` low.

## Success criteria
- One real hardware run passes.
- `PA4` shows the expected bounded pass waveform.
- The result is captured as a bounded PWM self-check proof on the STM32 anchor.

## Likely failure modes
- Missing `PA8 -> PB8` loopback
- Incorrect TIM1_CH1 configuration on `PA8`
- `PB8` sampling never sees both levels
- `PA4` pass/fail export logic misconfigured

## Regression framing
- Change class: `Class 3` bounded path-specific runtime change
- Affected anchor: `stm32f103` primary sample-board capability anchor
- Minimum regression tier: `Tier 4`

## Validation commands
```bash
python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/stm32f103_pwm_banner.json
python3 -m ael explain-stage --board stm32f103 --test tests/plans/stm32f103_pwm_banner.json --stage plan
python3 -m ael run --board stm32f103 --test tests/plans/stm32f103_pwm_banner.json
```
