# STM32F411CEU6 bring-up preparation note

This file is a target-specific preparation note, not the primary rule document.

Primary rules now live in:

- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
- [stm32_official_source_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32_official_source_generation_policy_v0_1.md)
- [first_time_mcu_test_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/first_time_mcu_test_generation_policy_v0_1.md)
- [stm32f411ceu6_bringup_preparation_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_preparation_v0_1.md)

## Intended use

Use this note before generating new STM32F411 board tests.

It exists to make one point explicit:

- STM32F103 is a useful AEL methodology reference
- STM32F103 is not the primary implementation source for STM32F411

## STM32F411 source anchor

Use STM32F411 official sources first:

- STM32F411xC/xE datasheet
- RM0383 STM32F411xC/E reference manual
- STM32CubeF4 device support and examples

The local STM32F411 target directory may help with file layout and prior
provenance, but should not replace official-source review during first-time
bring-up.

## Methodology anchor

For methodology, start from validated AEL patterns such as:

- `stm32f103_gpio_signature`
- `stm32f103_uart_banner`
- `stm32f103_adc_banner`

Reuse:

- staged validation structure
- proof/banner concepts
- evidence and connection-contract patterns

Do not automatically reuse:

- RCC enable bits
- alternate-function selections
- pin assignments
- timer or ADC register assumptions

## Required next artifact

Before new STM32F411 test generation, update and use:

- [stm32f411ceu6_bringup_preparation_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_bringup_preparation_v0_1.md)

That preparation document is the current source-oriented basis for the next
STM32F411 bring-up round.
