# STM32F103 Capture Self-Check v0.1

## Purpose
- add a bounded timing/capture proof on the unified STM32F103 capability fixture
- reuse the existing `PA8 -> PB8` loopback
- keep `PA4 -> P0.0` as the only external machine-checkable proof path

## Pin use
- `PA8 = TIM1_CH1` source output
- `PB8 = TIM4_CH3` capture input
- `PA8 -> PB8` manual loopback required
- `PA4 -> P0.0` external observe path

## Bounded success method
- firmware generates a stable `50 Hz` source on `PA8`
- firmware measures captured rising-edge periods on `PB8`
- if enough captured periods fall within the expected range, firmware treats the timing self-check as good
- firmware encodes capture-good status onto `PA4`
- AEL verifies the resulting `PA4` waveform

## External observation rule
- `PA8` and `PB8` are timing-internal self-check pins
- external proof remains on `PA4`
- `PA5 -> P0.1` is not needed for this path

## Validation commands
- `python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/stm32f103_capture_banner.json`
- `python3 -m ael explain-stage --board stm32f103 --test tests/plans/stm32f103_capture_banner.json --stage plan`
- `python3 -m ael run --board stm32f103 --test tests/plans/stm32f103_capture_banner.json`

## Regression framing
- change class: `Class 3`
- affected anchor: `stm32f103` primary sample-board capability anchor
- minimum regression tier: `Tier 4`

## What this path should prove
- bounded timer-capture/timing self-check on the unified STM32F103 fixture
- no new family setup
- no new instrument role

## What this path should not try to prove
- general timer framework support
- precision frequency measurement from ESP32JTAG
- external waveform analysis framework
