# STM32F411CEU6 Bring-Up Preparation v0.1

This document prepares STM32F411CEU6 support before final AEL test generation.

It is intentionally source-oriented and methodology-oriented. Unknowns are
labeled explicitly.

## Identity and family mapping

- target MCU: `stm32f411ceu6`
- target board: `STM32F411CEU6 WeAct Black Pill V2.0`
- STM32 family: `STM32F4`
- device line: `STM32F411xC/xE`
- core: Arm Cortex-M4 with FPU

Official basis:

- ST product page for `STM32F411CE`
- DS10314 `STM32F411xC/xE` datasheet
- RM0383 `STM32F411xC/E advanced Arm-based 32-bit MCUs`
- STM32CubeF4 package
- WeAct Black Pill board page provided by the user:
  `https://stm32-base.org/boards/STM32F411CEU6-WeAct-Black-Pill-V2.0.html`

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
- the board page indicates an onboard EEPROM footprint on:
  - `PA4`
  - `PB4`
  - `PA7`
  - `PA5`
  so these should not be the default reusable AEL pins unless the actual board
  population is verified

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

Current implementation-reference approach:

- use the WeAct Black Pill page for board-level breakout constraints
- use STM32CubeF4 `STM32F411E-Discovery` and `STM32F411RE-Nucleo` examples for
  official peripheral-function and initialization references

Reason:

- the WeAct page identifies the actual board used for AEL planning
- the local STM32CubeF4 cache contains the official peripheral examples needed
  to anchor GPIO, USART, SPI, ADC, and TIM setup
- Discovery/Nucleo example pin choices are acceptable as implementation
  references only when they map to pins also present and suitable on the WeAct
  board

## Official example categories to use

These should be used as implementation references, not as AEL board-policy
definitions.

### GPIO candidate references

Official STM32CubeF4 examples present locally:

- `Projects/STM32F411E-Discovery/Templates_LL`
- `Projects/STM32F411RE-Nucleo/Examples/GPIO/GPIO_IOToggle`
- `Projects/STM32F411RE-Nucleo/Examples_LL/GPIO/GPIO_InfiniteLedToggling`
- `Projects/STM32F411RE-Nucleo/Examples_LL/GPIO/GPIO_InfiniteLedToggling_Init`

Provisional starting reference:

- begin with `STM32F411E-Discovery/Templates_LL` for family/board template
  review, then borrow the simplest GPIO example structure from the STM32F411
  official trees

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
- prefer `USART1` on `PA9/PA10` for the one-setup AEL contract because the
  official `USART2` pair `PA2/PA3` is a likely better fit for direct probe
  observation

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
- keep the STM32F411E-Discovery ADC example only as an official family example,
  not as proof of final AEL pin or board wiring
- prefer `PB0 = ADC1_IN8` over `PA4 = ADC1_IN4` because `PA4` is in the WeAct
  board EEPROM-footprint caution set

## Confirmed peripheral-function candidates

These functions are anchored to official STM32CubeF4 examples already present
in the repo.

- SPI:
  - `PB13 = SPI2_SCK`
  - `PB14 = SPI2_MISO`
  - `PB15 = SPI2_MOSI`
- USART:
  - `PA2 = USART2_TX`
  - `PA3 = USART2_RX`
  - `PA9 = USART1_TX`
  - `PA10 = USART1_RX`
- ADC:
  - `PB0 = ADC1_IN8`
  - `PA4 = ADC1_IN4` but discouraged for default AEL use
- TIM:
  - `PA8 = TIM1_CH1`
  - `PA6 = TIM3_CH1`
  - `PA5 = TIM2_CH1` but discouraged for default AEL use

Recommended first AEL candidate groups:

- proof pins:
  - `PA2 -> P0.0`
  - `PA3 -> P0.1`
  - only these two should be always-connected initially
- SPI observation:
  - `PB13 -> P0.2`
- UART loopback:
  - `PA9 -> PA10`
- SPI loopback:
  - `PB15 -> PB14` with `PB13` as SCK
- ADC:
  - `PB1 -> PB0`
- PWM / EXTI / capture / generic loopback:
  - `PA8 -> PA6`

Status:

- peripheral functions listed above are officially anchored
- the final decision to use exactly these groups on the WeAct board is still an
  AEL bench-contract choice and needs bench confirmation

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

- actual USB/UART bridge path, if any
- which GPIOs are safely accessible on the physical board used by AEL
- whether a stable ADC external-input path already exists on the bench fixture

Confirmed from user bench knowledge:

- onboard LED is connected to `PC13`

## Recommended minimum test generation order

Recommended conservative order:

1. GPIO proof path
   - minimal output toggle based on official STM32F411 GPIO examples
   - AEL methodology borrowed from `stm32f103_gpio_signature`
2. UART banner path
   - minimal transmit-only banner first on `USART1 PA9/PA10`
   - official STM32F411 USART example as implementation basis
   - AEL methodology borrowed from `stm32f103_uart_banner`
3. ADC proof path
   - single-channel single-conversion first on `PB0 = ADC1_IN8`
   - LL example preferred as implementation basis
   - AEL methodology borrowed from `stm32f103_adc_banner`
4. only after these basics:
   - SPI
   - PWM
   - EXTI
   - capture
   - I2C

## Current inferred assumptions

These are not yet fully confirmed:

- `PA2/PA3` should be the only fixed proof-pin set for the initial bench
- `PA9/PA10` should be the permanent UART pair for the one-setup contract
- `PB1 -> PB0` is the best ADC source/input pair on the actual bench
- `PA8 -> PA6` is the accepted reusable timer/loopback pair for the current
  draft
- the EEPROM footprint is either absent or harmless enough to simply avoid its
  pins and not require additional board-specific handling

## Rejected implementation shortcuts

Rejected as primary basis:

- copying STM32F103 register-level code directly
- assuming F103 UART/GPIO/ADC pin choices are portable
- using an old local target as sufficient proof of STM32F411 implementation
  correctness

## Recommended next step

Before final STM32F411 test generation:

1. select the exact STM32F411 board/module variant used by AEL
2. confirm the proposed safe pin groups on the real WeAct board
3. keep `NRST` as `NC`
4. create a bring-up report using
   [first_time_mcu_bringup_report_template.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/templates/first_time_mcu_bringup_report_template.md)
5. refine the draft connection contract in
   [stm32f411ceu6_connection_contract_draft_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f411ceu6_connection_contract_draft_v0_1.md)
6. only then generate the first minimal GPIO path
