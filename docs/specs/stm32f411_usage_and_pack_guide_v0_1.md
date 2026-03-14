# STM32F411 Usage And Pack Guide v0.1

## Purpose

This note explains which STM32F411 path to use depending on the validation goal.

## Fastest F411 smoke path

Use:

- `packs/smoke_stm32f411.json`

Current content:

- `stm32f411_gpio_signature`

Use this when:

- you want a fast representative F411 bench-health check
- you want the same low-risk F411 baseline that is suitable for default verification

## Full F411 suite pack/helper

Use either:

- `packs/stm32f411_full_suite.json`
- `tools/run_stm32f411_full_suite.sh`

Use this when:

- you want the whole validated F411 suite in one invocation
- you want repeat board-health runs without rebuilding a shell loop by hand

## Representative default-verification role

Current default-verification representative:

- `stm32f411_gpio_signature`

Why this is the right representative:

- lowest-risk directly observed F411 baseline
- already validated repeatedly on live hardware
- exercises flash, boot, GPIO configuration, and logic-analyzer verification without requiring manual loopback jumpers

## Full F411 board-health suite

Use the full per-board suite when the goal is to validate the whole first-pass F411 feature set:

- `stm32f411_gpio_signature`
- `stm32f411_uart_loopback_banner`
- `stm32f411_adc_banner`
- `stm32f411_spi_banner`
- `stm32f411_gpio_loopback_banner`
- `stm32f411_pwm_banner`
- `stm32f411_exti_banner`
- `stm32f411_capture_banner`

Use this when:

- you changed F411 firmware or plans
- you changed F411 wiring
- you want board-health evidence beyond the default-verification baseline role

## Rule of thumb

- default verification:
  - one representative low-risk F411 baseline only
- smoke pack:
  - one representative low-risk F411 baseline only
- board bring-up / board health:
  - full eight-test F411 suite
