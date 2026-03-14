# STM32F411CEU6 Bring-Up Preparation v0.1

This document prepares STM32F411CEU6 support before final AEL test generation.

It is intentionally source-oriented and methodology-oriented. Unknowns are
labeled explicitly.

## Identity and family mapping

- target MCU: `stm32f411ceu6`
- STM32 family: `STM32F4`
- device line: `STM32F411xC/xE`
- core: Arm Cortex-M4 with FPU

Official basis:

- ST product page for `STM32F411CE`
- DS10314 `STM32F411xC/xE` datasheet
- RM0383 `STM32F411xC/E advanced Arm-based 32-bit MCUs`
- STM32CubeF4 package

## Package awareness

Confirmed from the ST product page:

- `STM32F411CEU6` package: `UFQFPN48 7x7x0.55 mm`

Implications:

- this is a smaller package than the 64-pin and 100-pin F411 variants
- not every family peripheral signal is bonded out on this package
- board-level pin choices must be package-aware, not family-generic

Official pinout evidence from DS10314 shows the UFQFPN48 package includes pins
such as:

- `PA0..PA10` with some gaps depending on package table rows
- `PB0..PB15` with package-specific omissions
- `PC13`, `PC15`
- `BOOT0`, `NRST`, `VCAP_1`, `VDDA`, `VREF+`

Known caution:

- exact safe GPIO/UART/ADC pin picks for the actual board/module still need
  board-level verification
- package presence does not guarantee the module breaks that pin out cleanly

## Official SDK family/package to use

Recommended official package:

- `STM32CubeF4`

Local repo evidence:

- `third_party/cache/STM32CubeF4`

Relevant official support already present locally:

- CMSIS/device headers for `STM32F411xE`
- `startup_stm32f411xe.s`
- `system_stm32f4xx.c`
- official STM32F411 Discovery, Nucleo, and LL example trees

## Official example categories to use

These should be used as implementation references, not as AEL board-policy
definitions.

### GPIO candidate references

Official STM32CubeF4 examples present locally:

- `Projects/STM32F411RE-Nucleo/Examples/GPIO/GPIO_IOToggle`
- `Projects/STM32F411RE-Nucleo/Examples_LL/GPIO/GPIO_InfiniteLedToggling`
- `Projects/STM32F411RE-Nucleo/Examples_LL/GPIO/GPIO_InfiniteLedToggling_Init`

Recommended use:

- use these to anchor GPIO enable, mode configuration, and safe minimal
  toggling flow
- do not copy their LED pin assumptions directly onto the target board

### UART candidate references

Official STM32CubeF4 examples present locally:

- `Projects/STM32F411RE-Nucleo/Examples/UART/UART_Printf`
- `Projects/STM32F411E-Discovery/Examples/UART/UART_TwoBoards_ComPolling`
- `Projects/STM32F411RE-Nucleo/Examples_LL/USART/USART_Communication_Tx`
- `Projects/STM32F411RE-Nucleo/Examples_LL/USART/USART_Communication_Rx_IT`

Recommended use:

- use these to anchor USART enablement, GPIO AF setup, and basic transmit or
  banner output structure
- choose the simplest path first, likely transmit-first rather than a more
  complex two-board or DMA path

### ADC candidate references

Official STM32CubeF4 examples present locally:

- `Projects/STM32F411E-Discovery/Examples/ADC/ADC_RegularConversion_DMA`
- `Projects/STM32F411RE-Nucleo/Examples_LL/ADC/ADC_SingleConversion_TriggerSW`
- `Projects/STM32F411RE-Nucleo/Examples_LL/ADC/ADC_ContinuousConversion_TriggerSW`
- `Projects/STM32F411RE-Nucleo/Examples_LL/ADC/ADC_SingleConversion_TriggerSW_IT`

Recommended use:

- use the LL single-conversion examples as the likely minimum-complexity
  implementation basis for a first ADC proof path
- avoid starting with DMA unless the simpler path is blocked

## AEL methodology basis

Recommended methodology sources from validated AEL work:

- `stm32f103_gpio_signature`
- `stm32f103_uart_banner`
- `stm32f103_adc_banner`
- general staged bring-up flow from
  [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)

What may be borrowed from STM32F103 methodology:

- start with a minimal proof path first
- keep tests verification-friendly
- prefer explicit pass/fail signals or ready banners
- keep connection contracts formal and inventory-visible
- separate `plan`, `pre-flight`, `run`, and `check`
- capture evidence and last-known-good setup after first success

## What must not be borrowed from STM32F103 implementation

Do not assume the following are portable from STM32F103:

- RCC register layout or enable-bit names
- GPIO register layout
- AFIO versus STM32F4 alternate-function model
- USART pin defaults
- ADC control register layout
- timer configuration details
- linker memory sizes
- LED or proof pin choices

These must be justified from STM32F411 official sources instead.

## Likely drift risks

Known or likely drift to review before generation:

- `STM32F1` to `STM32F4` GPIO/register model drift
- alternate-function selection model drift
- package-level pin availability drift
- UART pin breakout drift on the actual module/board
- ADC channel availability on the actual board header set
- boot/reset wiring differences on the actual board/module
- module vendor variation if the board is a BlackPill-like clone rather than an
  ST reference board

Unknowns requiring verification:

- actual LED pin on the board, if any
- actual USB/UART bridge path, if any
- which GPIOs are safely accessible on the physical board used by AEL
- whether a stable ADC external-input path already exists on the bench fixture

## Recommended minimum test generation order

Recommended conservative order:

1. GPIO proof path
   - minimal output toggle based on official STM32F411 GPIO examples
   - AEL methodology borrowed from `stm32f103_gpio_signature`
2. UART banner path
   - minimal transmit-only banner first
   - official STM32F411 USART example as implementation basis
   - AEL methodology borrowed from `stm32f103_uart_banner`
3. ADC proof path
   - single-channel single-conversion first
   - LL example preferred as implementation basis
   - AEL methodology borrowed from `stm32f103_adc_banner`
4. only after these basics:
   - PWM
   - EXTI
   - capture
   - SPI
   - I2C

## Current inferred assumptions

These are not yet fully confirmed:

- the simplest first GPIO path can likely use a directly observed output rather
  than internal loopback
- a Nucleo/Discovery official example can be mined for implementation logic
  while ignoring its board LED selection
- a UART transmit-only banner path is likely safer than a full loopback path
  for first UART bring-up
- LL ADC examples are likely a better first implementation basis than HAL DMA
  ADC examples

## Rejected implementation shortcuts

Rejected as primary basis:

- copying STM32F103 register-level code directly
- assuming F103 UART/GPIO/ADC pin choices are portable
- using an old local target as sufficient proof of STM32F411 implementation
  correctness

## Recommended next step

Before final STM32F411 test generation:

1. select the exact STM32F411 board/module variant used by AEL
2. confirm accessible pins and any onboard LED/UART bridge facts
3. choose the first GPIO proof pin from the actual board, not from another STM32
4. create a bring-up report using
   [first_time_mcu_bringup_report_template.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/templates/first_time_mcu_bringup_report_template.md)
5. only then generate the first minimal GPIO path
