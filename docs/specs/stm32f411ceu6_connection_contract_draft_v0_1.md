# STM32F411CEU6 Connection Contract Draft v0.1

This document defines the proposed one-setup hardware contract for STM32F411CEU6
bring-up in AEL.

It is a draft contract. Only explicitly marked items should be treated as
confirmed.

## Board identity

Use the following physical board as the current AEL target:

- `STM32F411CEU6 WeAct Black Pill V2.0`

Board-level facts currently accepted for this draft:

- onboard LED is connected to `PC13`
- SWD is available on `PA13/PA14`
- the board page exposes `PA0..PA10`, `PB0..PB15`, and `PC13..PC15`

Board-level caution from the referenced board page:

- the onboard EEPROM footprint uses:
  - `/CS -> PA4`
  - `DO -> PB4`
  - `DI -> PA7`
  - `CLK -> PA5`

Until the actual board population is verified on the bench, avoid using
`PA4/PA5/PA7/PB4` as the default reusable AEL test pins.

## Goal

Use one main STM32F411 hardware setup for:

- GPIO signature
- ADC
- SPI
- PWM
- EXTI
- capture
- UART loopback

If a future UART banner path requires a separate USB-UART fixture or a separate
physical DUT, that should be modeled as a separate DUT instance rather than
overloading this one-setup contract.

## Confirmed facts

- target board is `STM32F411CEU6 WeAct Black Pill V2.0`
- onboard LED is connected to `PC13`
- SPI2 pin function from official STM32CubeF4 examples:
  - `PB13 = SPI2_SCK`
  - `PB14 = SPI2_MISO`
  - `PB15 = SPI2_MOSI`
- USART2 pin function from official STM32CubeF4 examples:
  - `PA2 = USART2_TX`
  - `PA3 = USART2_RX`
- USART1 pin function from official STM32CubeF4 examples:
  - `PA9 = USART1_TX`
  - `PA10 = USART1_RX`
- ADC examples confirm:
  - `PB0 = ADC1_IN8`
  - `PA4 = ADC1_IN4` but `PA4` is currently discouraged by the board EEPROM
    caution above
- timer examples confirm:
  - `PA5 = TIM2_CH1` but `PA5` is currently discouraged by the board EEPROM
    caution above
  - `PA6 = TIM3_CH1`
  - `PA8 = TIM1_CH1`

## Fixed wiring

These should remain connected for most tests.

- `SWD -> P3`
- `RESET -> NC`
- `GND -> probe GND`
- `PA2 -> P0.0` as `MAIN_PROOF_PIN`
- `PA3 -> P0.1` as `SECONDARY_PROOF_PIN`
- `PC13 -> LED`

Status of this fixed wiring proposal:

- `PA2/PA3` are the confirmed always-connected proof pins for the current draft
- `P0.2` and `P0.3` should remain unconnected in the initial setup
- `PA2/PA3` are officially valid USART2 pins, so using them as permanent proof
  pins conflicts with using `USART2` for UART tests on the same one-setup
  contract

## Reusable jumper pairs

These are test-specific manual jumpers layered on top of the fixed wiring.

### ADC jumper

- selected: `PB1 -> PB0`

Meaning:

- `PB1` as `ADC_SOURCE_PIN` driven by firmware as a digital source
- `PB0` as `ADC_INPUT_PIN`
- official STM32CubeF4 ADC example confirms `PB0 = ADC1_IN8`

Status:

- `PB0` analog capability is officially confirmed
- `PB1 -> PB0` is the intended ADC source/input pair for the current draft

### Generic digital loopback jumper

- selected: `PA8 -> PA6`

This pair should be reused where practical for:

- generic GPIO loopback
- PWM self-check
- EXTI self-check
- capture self-check

Status:

- `PA8` timer-output role is officially confirmed
- `PA6` timer-input role is officially confirmed
- `PA8 -> PA6` is accepted as the shared loopback pair for the current AEL
  STM32F411 draft

### SPI loopback jumper

- proposed: `PB15 -> PB14`

Official confirmation:

- `PB13 = SPI2_SCK`
- `PB14 = SPI2_MISO`
- `PB15 = SPI2_MOSI`

Recommended SPI usage:

- `PB13` as `SPI_SCK_PIN`
- `PB15` as `SPI_MOSI_PIN`
- `PB14` as `SPI_MISO_PIN`
- loopback jumper: `PB15 -> PB14`

This is the cleanest confirmed SPI choice so far and avoids the discouraged
`PA5/PA7/PB4` board-footprint pins.

### UART loopback jumper

- proposed: `PA9 -> PA10`

Official confirmation:

- `PA9 = USART1_TX`
- `PA10 = USART1_RX`

Reason:

- `USART1` on `PA9/PA10` avoids the direct conflict between:
  - `PA2/PA3` as always-connected proof pins
  - `PA2/PA3` as `USART2 TX/RX`

## Proposed role model

### Direct-observation roles

- `MAIN_PROOF_PIN`
  - primary proof/output capture pin
  - preferred pass/fail export for self-check tests
- `SECONDARY_PROOF_PIN`
  - second observed signal for GPIO signature or ratio checks
- `AUX_PROOF_PIN_1`
  - optional additional observed signal, currently unassigned
- `AUX_PROOF_PIN_2`
  - optional additional observed signal, currently unassigned

## Confirmed peripheral-function table

These pin functions are confirmed from official STM32CubeF4 example sources.

| Function | Pin(s) | Official basis | Status in AEL draft |
| --- | --- | --- | --- |
| `SPI2` | `PB13 SCK`, `PB14 MISO`, `PB15 MOSI` | STM32F411E-Discovery SPI example | preferred SPI basis |
| `USART2` | `PA2 TX`, `PA3 RX` | STM32F411E-Discovery UART example | confirmed, but conflicts with proof-pin proposal |
| `USART1` | `PA9 TX`, `PA10 RX` | STM32F411RE-Nucleo LL USART example | preferred UART basis |
| `ADC1_IN8` | `PB0` | STM32F411E-Discovery ADC example | preferred ADC input basis |
| `ADC1_IN4` | `PA4` | STM32F411RE-Nucleo LL ADC example | confirmed, but discouraged by board EEPROM caution |
| `TIM1_CH1` | `PA8` | STM32F411RE-Nucleo LL TIM example | confirmed timer-output candidate |
| `TIM3_CH1` | `PA6` | STM32F411RE-Nucleo LL TIM example | confirmed timer-input candidate |
| `TIM2_CH1` | `PA5` | STM32F411RE-Nucleo LL TIM example | confirmed, but discouraged by board EEPROM caution |

### Test intent by role

- `gpio_signature`
  - directly observe `PA2`
  - directly observe `PA3`
- `adc`
  - export bounded proof on `PA2`
  - use `PB1 -> PB0`
- `spi`
  - export bounded proof on `PA2`
  - use `PB15 -> PB14`
  - use `PB13` as `SPI_SCK_PIN`
- `pwm`
  - export bounded proof on `PA2`
  - use `PA8 -> PA6`
- `exti`
  - export bounded proof on `PA2`
  - use `PA8 -> PA6`
- `capture`
  - export bounded proof on `PA2`
  - use `PA8 -> PA6`
- `uart_loopback`
  - export bounded proof on `PA2`
  - use `PA9 -> PA10`

## Pin-selection rules

When filling the placeholders with real pins:

- prefer one stable proof pin reused across most self-check tests
- prefer one reusable digital loopback pair reused across multiple tests
- keep direct-observation pins distinct from jumper-driven self-check input pins
- do not reuse `PC13` as a primary proof pin just because it drives the onboard
  LED
- do not assume `USART2` on `PA2/PA3` can coexist with permanent proof-pin use
  on the same one-setup contract
- do not assume STM32F103 pin choices are portable
- avoid `PA4/PA5/PA7/PB4` by default because of the WeAct board EEPROM caution

## Unresolved placeholders

These still need board-level confirmation:

- whether the EEPROM footprint is populated on the actual WeAct board used by
  AEL
- whether any separate UART-banner fixture should use `USART1` or a different
  UART path

## Recommended next step

Before final STM32F411 test generation:

1. identify the exact physical STM32F411 board/module used by AEL
2. confirm whether the EEPROM footprint is populated on that board
3. keep `PA2/PA3` as the initial always-connected proof pins
4. keep `PB1 -> PB0` as the ADC pair
5. keep `PB13/PB14/PB15` as the SPI2 group
6. keep `PA9/PA10` as the UART pair
7. keep `PA8/PA6` as the shared loopback pair for PWM / EXTI / capture
8. update the board config and test plans only after those pins are frozen
