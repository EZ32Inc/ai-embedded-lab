# STM32F411CEU6 Repeat Validation Note 2026-03-14

## Purpose

Record the repeat-pass evidence for the first bounded STM32F411 suite after
bring-up closeout.

## Result

The full eight-test STM32F411 suite passed again on live hardware.

Repeat suite run ids:

- `stm32f411_gpio_signature`
  - `2026-03-14_10-13-11_stm32f411ceu6_stm32f411_gpio_signature`
- `stm32f411_uart_loopback_banner`
  - `2026-03-14_10-13-39_stm32f411ceu6_stm32f411_uart_loopback_banner`
- `stm32f411_adc_banner`
  - `2026-03-14_10-14-08_stm32f411ceu6_stm32f411_adc_banner`
- `stm32f411_spi_banner`
  - `2026-03-14_10-14-34_stm32f411ceu6_stm32f411_spi_banner`
- `stm32f411_gpio_loopback_banner`
  - `2026-03-14_10-15-10_stm32f411ceu6_stm32f411_gpio_loopback_banner`
- `stm32f411_pwm_banner`
  - `2026-03-14_10-15-50_stm32f411ceu6_stm32f411_pwm_banner`
- `stm32f411_exti_banner`
  - `2026-03-14_10-16-25_stm32f411ceu6_stm32f411_exti_banner`
- `stm32f411_capture_banner`
  - `2026-03-14_10-17-08_stm32f411ceu6_stm32f411_capture_banner`

## What this upgrades

- the bounded first-pass STM32F411 suite is now strong enough to describe as
  `repeat-pass`
- this supports the F411 capability anchor note and the current usage guidance

## Notes

- an extra repeat loop was intentionally stopped after sufficient evidence was
  obtained, to avoid unnecessary bench occupation
- this note is a repeat-evidence companion to:
  - `docs/specs/stm32f411ceu6_bringup_report_round3_closeout_v0_1.md`
