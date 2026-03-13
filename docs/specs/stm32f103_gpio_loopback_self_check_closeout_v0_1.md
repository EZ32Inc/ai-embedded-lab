# STM32F103 GPIO Loopback Self-Check Closeout v0.1

## Path
- board: `stm32f103`
- fixture: `stm32f103_unified_capability_fixture_v0_1`
- firmware target: `firmware/targets/stm32f103_gpio_loopback`
- test plan: `tests/plans/stm32f103_gpio_loopback_banner.json`

## Wiring used
- external observe:
  - `PA4 -> P0.0`
  - optional auxiliary observe: `PA5 -> P0.1`
- preserved fixture loopbacks:
  - `PA1 -> PA0`
  - `PA9 -> PA10`
  - `PA7 -> PA6`
- GPIO loopback:
  - `PA8 -> PB8`

## Bounded success method
- firmware drives a bounded digital pattern on:
  - `PA8`
- firmware samples the looped-back input on:
  - `PB8`
- firmware exports GPIO loopback pass/fail status on:
  - `PA4`
- AEL verifies `PA4` through the existing external observe path

## Live result
- run id: `2026-03-13_11-04-57_stm32f103_stm32f103_gpio_loopback_banner`
- result: `PASS`
- verify summary:
  - `edges=25`
  - `high=33575`
  - `low=31957`
  - `window=0.252s`

## What this proves
- the unified STM32 capability fixture can support a bounded GPIO self-check on `PA8 -> PB8` without new instrument roles
- `PA8 -> PB8` works as an internal digital loopback path
- `PA4` continues to serve as the main external machine-checkable proof signal
- the STM32F103 capability anchor now has bounded live-pass execution evidence for:
  - GPIO golden
  - UART
  - ADC
  - SPI
  - PWM
  - GPIO loopback

## What this does not prove
- unrestricted repeat-pass stability for the GPIO loopback path
- EXTI behavior on `PA8 -> PB8`
- capture/timing behavior on `PA8 -> PB8`

## Recommended next path
- `PA8 -> PB8` follow-on self-checks that reuse the same loopback:
  - EXTI
  - capture/timing-class demos
