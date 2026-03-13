# STM32F103 PWM Self-Check Closeout v0.1

## Path
- board: `stm32f103`
- fixture: `stm32f103_unified_capability_fixture_v0_1`
- firmware target: `firmware/targets/stm32f103_pwm`
- test plan: `tests/plans/stm32f103_pwm_banner.json`

## Wiring used
- external observe:
  - `PA4 -> P0.0`
  - optional auxiliary observe: `PA5 -> P0.1`
- preserved fixture loopbacks:
  - `PA1 -> PA0`
  - `PA9 -> PA10`
  - `PA7 -> PA6`
- PWM loopback:
  - `PA8 -> PB8`

## Bounded success method
- firmware generates PWM on:
  - `PA8 = TIM1_CH1`
- firmware samples looped-back high/low states on:
  - `PB8`
- firmware exports PWM pass/fail status on:
  - `PA4`
- AEL verifies `PA4` through the existing external observe path

## Live result
- run id: `2026-03-13_10-41-01_stm32f103_stm32f103_pwm_banner`
- result: `PASS`
- verify summary:
  - `edges=25`
  - `high=31788`
  - `low=33744`
  - `window=0.252s`

## What this proves
- the unified STM32 capability fixture can support a bounded PWM self-check without new instrument roles
- `PA8 -> PB8` works as an internal timing/self-check loopback
- `PA4` continues to serve as the main external machine-checkable proof signal
- the STM32F103 capability anchor now has bounded live-pass execution evidence for:
  - GPIO
  - UART
  - ADC
  - SPI
  - PWM

## What this does not prove
- unrestricted repeat-pass stability for the PWM path
- general timer/capture framework support
- direct external validation of PA8/PB8 timing beyond the bounded self-check

## Recommended next path
- `PA8 -> PB8` follow-on self-checks that reuse the same loopback:
  - GPIO self-check
  - EXTI
  - capture/timing-class demos
