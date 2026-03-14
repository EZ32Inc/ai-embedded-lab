# STM32F411CEU6 Capability Anchor Status v0.1

## Current board role
- current STM32F4 capability anchor for the first WeAct Black Pill bring-up wave
- index of record for the completed first-pass STM32F411 self-check phase

## Phase state
- the first bounded STM32F411 bring-up phase is complete

## Capability index

| Demo/path name | Status | Proof method | Result record | Closeout |
| --- | --- | --- | --- | --- |
| `stm32f411_gpio_signature` | `repeat-pass` | external GPIO signature observed on `PA2 -> P0.0` and `PA3 -> P0.1` | run history under `runs/...`, including `2026-03-14_09-22-08_stm32f411ceu6_stm32f411_gpio_signature` and `2026-03-14_10-13-12_stm32f411ceu6_stm32f411_gpio_signature` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_uart_loopback_banner` | `repeat-pass` | `PA9 -> PA10` internal UART loopback, result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-22-45_stm32f411ceu6_stm32f411_uart_loopback_banner` and `2026-03-14_10-13-35_stm32f411ceu6_stm32f411_uart_loopback_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_adc_banner` | `repeat-pass` | `PB1 -> PB0` ADC closed-loop, ADC-validated result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-23-10_stm32f411ceu6_stm32f411_adc_banner` and `2026-03-14_10-14-08_stm32f411ceu6_stm32f411_adc_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_spi_banner` | `repeat-pass` | `PB15 -> PB14` SPI2 loopback with result encoded onto `PA2`; auxiliary SCK visibility on `PB13 -> P0.2` | run history under `runs/...`, including `2026-03-14_09-23-37_stm32f411ceu6_stm32f411_spi_banner` and `2026-03-14_10-14-36_stm32f411ceu6_stm32f411_spi_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_gpio_loopback_banner` | `repeat-pass` | `PA8 -> PA6` internal GPIO loopback, result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-24-08_stm32f411ceu6_stm32f411_gpio_loopback_banner` and `2026-03-14_10-15-03_stm32f411ceu6_stm32f411_gpio_loopback_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_pwm_banner` | `repeat-pass` | `PA8 -> PA6` internal PWM loopback, result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-24-35_stm32f411ceu6_stm32f411_pwm_banner` and `2026-03-14_10-15-26_stm32f411ceu6_stm32f411_pwm_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_exti_banner` | `repeat-pass` | `PA8 -> PA6` internal EXTI self-check, result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-24-58_stm32f411ceu6_stm32f411_exti_banner` and `2026-03-14_10-16-24_stm32f411ceu6_stm32f411_exti_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |
| `stm32f411_capture_banner` | `repeat-pass` | `PA8 -> PA6` internal capture/timing self-check, result encoded onto `PA2` | run history under `runs/...`, including `2026-03-14_09-25-25_stm32f411ceu6_stm32f411_capture_banner` and `2026-03-14_10-17-08_stm32f411ceu6_stm32f411_capture_banner` | [stm32f411ceu6_bringup_report_round3_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md) |

## Summary
- the full first-pass STM32F411 suite is materially stable
- the representative default-verification role remains:
  - `stm32f411_gpio_signature`
- the current validated loopback families are:
  - UART on `PA9 -> PA10`
  - ADC on `PB1 -> PB0`
  - SPI on `PB15 -> PB14`
  - GPIO/PWM/EXTI/capture on `PA8 -> PA6`

## Status boundary
- the bounded first-pass STM32F411 bring-up set is now `repeat-pass`
- no additional first-wave F411 path is required before a new review/expansion decision

## What should happen next
- keep `stm32f411_gpio_signature` as the representative F411 default-verification step
- use `packs/smoke_stm32f411.json` for a fast F411 smoke path
- use the full eight-test suite when the goal is F411 board-health validation rather than baseline orchestration
