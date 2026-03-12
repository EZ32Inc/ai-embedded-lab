# Generated Example Blocker Groups v0.1

## Purpose

This note groups the current blockers that prevent generated examples from
moving directly into execution work.

## Blocker Group 1: Missing Hardware Provisioning

Examples in this group are structurally ready enough, but lack a real bench
setup path for execution.

Examples:
- `rp2040_uart_banner`
- `stm32f103_uart_banner`
- generated RP2/STM32 SPI and I2C examples that still need explicit bench setup

## Blocker Group 2: Missing Formal Contract Completion

Examples in this group are generated and build-valid, but still lack one
critical formal connection contract detail.

Examples:
- ADC examples with no explicit external analog-input source defined

Recommended first target:
- `stm32f103_adc_banner`

## Blocker Group 3: Unstable Bench Path

Examples in this group can be generated and staged correctly, but runtime
claims should remain conservative because the bench path is unstable.

Examples:
- ESP32 generated examples on the current meter-backed path

## Working Rule

The next execution-facing batch should remove one blocker from one group.
