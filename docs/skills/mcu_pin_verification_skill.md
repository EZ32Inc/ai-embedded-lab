# MCU Pin Verification Skill

## Purpose

`mcu_pin_verification` ensures that peripheral-to-pin assignments for a new MCU target
are confirmed from authoritative sources before any firmware, config, or wiring plan
is written.

**Rule: never copy pin assignments from a related chip without verification.**

Even within the same MCU family (e.g. STM32F4xx), individual variants may differ in
available peripherals, AF mapping, or package constraints. This skill defines what to
check, where to check it, and how to record the result.

---

## When To Use

Invoke this skill whenever:

- adding a new MCU or board to AEL firmware targets
- deriving a new board config from an existing one in the same family
- writing any firmware that relies on peripheral alternate functions (UART, SPI, TIM, ADC)
- a wiring plan references specific MCU pins for instrument connection

Do not skip this step because the new chip is "similar to" an existing validated target.
Similarity is not confirmation.

---

## Verification Source Hierarchy

Use sources in this order. Stop at the first level that gives direct, chip-specific evidence.

### Level 1 — Official STM32Cube example for the exact chip

Location in this repo: `third_party/cache/STM32CubeF4/Projects/<board>/Examples/<peripheral>/`

These are the strongest source. They are written for a specific device and contain
actual HAL `GPIO_InitStruct.Alternate`, pin number, and port definitions.

What to look for:
- `Inc/main.h` — defines `xxx_PIN`, `xxx_GPIO_PORT`, `xxx_AF`
- `Src/stm32f4xx_hal_msp.c` — contains `GPIO_InitStruct.Alternate = GPIO_AFx_xxx`

Examples already present:

| Peripheral | F401 project path |
|---|---|
| SPI2 | `STM32F401-Discovery/Examples/SPI/SPI_FullDuplex_ComIT/Inc/main.h` |
| USART2 | `STM32F401-Discovery/Examples/UART/UART_TwoBoards_ComIT/Inc/main.h` |
| ADC1 | `STM32F401-Discovery/Examples/ADC/ADC_RegularConversion_DMA/Inc/main.h` |
| TIM (PWM) | `STM32F401-Discovery/Examples/TIM/TIM_PWMInput/Inc/main.h` |

### Level 2 — HAL GPIO extension header for the exact device define

File: `third_party/cache/STM32CubeF4/Drivers/STM32F4xx_HAL_Driver/Inc/stm32f4xx_hal_gpio_ex.h`

Search for the `#if defined(STM32F4xxxx)` block for your target.
This lists which AF numbers are defined (e.g. `GPIO_AF5_SPI2`, `GPIO_AF7_USART1`)
but does NOT tell you which specific pin carries each function.

Use Level 2 to confirm: "does this AF number exist on this device?"
Do NOT use Level 2 alone to conclude which pin carries it.

### Level 3 — Cross-family Nucleo or EVAL example (same AF structure)

When no chip-specific example exists for the exact variant, look at a closely related
chip in the same sub-family. Accept this as evidence only when:

- the chips share the same AF mapping table (confirmed by HAL header — same `#if defined` block)
- the example explicitly states the pin (e.g. in a readme.txt: `TIM1_CH1 pin (PA.08)`)

Mark these as "F4 family standard" in the verification table, not as "confirmed".

### Level 4 — STM32 Reference Manual alternate function table

If no Cube example exists at all, consult the RM's GPIO alternate function table
(Table xx in the RM for your specific part number).

This is the definitive ground truth but requires manual lookup and is not automated.

---

## What Must Be Verified Per Peripheral

For each peripheral used in AEL experiments, confirm:

| Peripheral | What to confirm | Risk if wrong |
|---|---|---|
| **SPI (SCK/MISO/MOSI)** | Port, pin number, AF number | Wrong bytes, no clock |
| **USART/UART (TX/RX)** | Port, pin number, AF number | No output or garbage |
| **TIM PWM output** | Port, pin, AF, timer number, channel | No waveform |
| **TIM input capture** | Port, pin, AF, timer number, channel | Capture reads nothing |
| **EXTI** | Port, pin (any GPIO can be EXTI, but verify no conflict) | No interrupt |
| **ADC** | Port, pin, ADC channel number | Wrong voltage reading |
| **GPIO output (proof pin)** | Just confirm no alternate-function conflict on that pin | Proof signal lost |

---

## Verification Table Format

After running this skill, produce a table in this format:

```
| Pin  | Function           | Peripheral | AF  | Source                        | Confidence       |
|------|--------------------|-----------|-----|-------------------------------|------------------|
| PA2  | GPIO / USART2_TX   | USART2    | AF7 | F401 UART example main.h      | confirmed        |
| PA8  | TIM1_CH1 PWM out   | TIM1      | AF1 | STM324xG readme.txt + HAL hdr | family-standard  |
| PB0  | ADC1_IN8           | ADC1      | —   | F401 ADC example main.h       | confirmed        |
```

Confidence levels:
- **confirmed** — direct evidence in chip-specific Cube example
- **family-standard** — consistent across the sub-family, no chip-specific example found
- **inferred** — derived from AF header only, no example code found — flag for manual check

---

## STM32 Family Notes

### STM32F4xx (F401, F405, F407, F411, F446, etc.)

- SPI2 on PB13/PB14/PB15 is consistent across the whole F4 family
- TIM1_CH1 on PA8 (AF1) is consistent across the whole F4 family
- TIM3_CH1 on PA6 (AF2) is consistent across the whole F4 family
- USART1 on PA9/PA10 (AF7) is consistent across the whole F4 family
- USART2 on PA2/PA3 (AF7) is consistent across the whole F4 family
- ADC1_IN8 on PB0, ADC1_IN9 on PB1 is consistent across the whole F4 family
- **Differences to watch:**
  - Flash/RAM size differs (F401: 256/512K, F411: 512K, F405/407: 1M)
  - Some peripherals absent on smaller variants (e.g. F401 has no DAC)
  - Package constraints: 48-pin (CEU6) vs 64-pin (RCT6) exposes different pins
  - F401 max clock 84 MHz, F411 max clock 100 MHz — affects timer/UART dividers

Cube path: `third_party/cache/STM32CubeF4/Projects/`
Relevant boards: `STM32F401-Discovery/`, `STM32F411RE-Nucleo/`, `STM324xG_EVAL/`

### STM32F1xx (F103, F105, F107, etc.)

- F1 uses a different GPIO model: no AFIO register per-pin, uses AFIO remap registers
- SPI1 default: PA5 (SCK), PA6 (MISO), PA7 (MOSI) — remappable to PB3/PB4/PB5
- SPI2: PB13 (SCK), PB14 (MISO), PB15 (MOSI) — same as F4, no remap needed
- USART1 default: PA9 (TX), PA10 (RX) — remappable to PB6/PB7
- USART2 default: PA2 (TX), PA3 (RX) — same as F4
- TIM1_CH1: PA8 — same physical pin as F4 but different AF mechanism
- ADC channel mapping is the same (PA0=IN0, PB0=IN8, etc.)
- **Key difference vs F4:** F1 does not have per-pin AF selection in MODER/AFR.
  Instead, remap is controlled by the AFIO_MAPR register. The firmware approach
  is completely different even if pin names look the same.
- **Do not copy F4 GPIO init code to F1 targets.** The register layout is incompatible.

Cube path: `third_party/cache/STM32CubeF1/Projects/` (if present)
Fallback: check `STM32F103` existing AEL targets for proven patterns.

### STM32G4xx, STM32L4xx, STM32H7xx

- Use the same per-pin AF model as F4 (MODER + AFR registers)
- But AF numbers differ — GPIO_AF5_SPI2 on F4 may be a different AF on G4/H7
- Always consult the chip-specific `stm32f4xx_hal_gpio_ex.h` equivalent
- Do not assume AF numbers are portable across series

---

## Checklist Before Writing Firmware Or Config

- [ ] Identified all peripheral pins needed for this board's experiments
- [ ] Verified each pin at Level 1 or Level 2 (not assumed from a related board)
- [ ] Produced a verification table with source and confidence for each entry
- [ ] Flagged any "inferred" entries for manual datasheet check
- [ ] Confirmed package constraints (all needed pins accessible in this package)
- [ ] Confirmed no pin conflicts between experiments (e.g. SPI SCK and TIM complementary on same pin)
- [ ] Noted any peripherals that are absent on this variant (e.g. no DAC on F401)

---

## Relationship To Other Skills

- **new_board_bringup_skill**: calls this skill at step 2 ("Anchor implementation facts
  to official vendor sources") before any firmware or config is written
- **capability_expansion_skill**: should invoke this skill when adding new peripheral
  experiments to an existing board target
- **copy_first_system_branch_growth**: when deriving a new board from an existing path,
  this skill is the gate that prevents incorrect pin assumptions from propagating

---

## Example: STM32F401RCT6 Verification Session (2026-03-15)

This skill was first formalized after the F401 bring-up session where the AI was
asked "have you actually verified these pins for F401, or just copied from F411?"

Sources consulted:
- `STM32F401-Discovery/Examples/SPI/SPI_FullDuplex_ComIT/Inc/main.h` → PB13/14/15 confirmed
- `STM32F401-Discovery/Examples/UART/UART_TwoBoards_ComIT/Inc/main.h` → PA2/PA3 (USART2) confirmed
- `STM32F401-Discovery/Examples/ADC/ADC_RegularConversion_DMA/Inc/main.h` → PB0/ADC1_IN8 confirmed
- `STM32F411RE-Nucleo/Examples_LL/USART/USART_Communication_Tx/Inc/main.h` → PA9/PA10 (USART1 AF7) confirmed
- `STM324xG_EVAL/Examples/TIM/TIM_ComplementarySignals/readme.txt` → PA8 = TIM1_CH1 confirmed

Result: all F411 experiment pins are valid on F401RCT6. Note: PA6/TIM3_CH1 and
PB1/ADC1_IN9 were confirmed as "family-standard" only — direct F401 example not found.
