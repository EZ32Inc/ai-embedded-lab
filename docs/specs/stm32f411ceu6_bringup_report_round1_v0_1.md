# STM32F411CEU6 Bring-Up Report Round 1 v0.1

## Identity

- MCU: `stm32f411ceu6`
- board/module: `STM32F411CEU6 WeAct Black Pill V2.0`
- package: `UFQFPN48`
- board family: `STM32F4 / STM32F411xC/xE`
- DUT instance or bench target: `stm32f411ceu6`
- report date: `2026-03-14`
- author: `Codex`

## Scope of this round

- goal of this bring-up round:
  - freeze the real bench contract
  - generate the first minimal GPIO signature path
  - run the first hardware validation round
- what is intentionally out of scope:
  - UART banner
  - ADC
  - SPI
  - PWM
  - EXTI
  - capture
  - I2C

## Official source basis

- datasheet:
  - `DS10314 STM32F411xC/xE`
- reference manual:
  - `RM0383 STM32F411xC/E`
- programming manual:
  - CMSIS/device programming model via official STM32CubeF4 package
- official SDK/package:
  - `STM32CubeF4`
- official startup/system source:
  - `startup_stm32f411xe.s`
  - `system_stm32f4xx.c`
- official example paths reviewed:
  - `Projects/STM32F411E-Discovery/Examples/SPI/SPI_FullDuplex_ComPolling`
  - `Projects/STM32F411E-Discovery/Examples/UART/UART_TwoBoards_ComPolling`
  - `Projects/STM32F411E-Discovery/Examples/ADC/ADC_RegularConversion_DMA`
  - `Projects/STM32F411RE-Nucleo/Examples_LL/USART/USART_Communication_Tx`
  - `Projects/STM32F411RE-Nucleo/Examples_LL/ADC/ADC_SingleConversion_TriggerSW`
  - `Projects/STM32F411RE-Nucleo/Examples_LL/TIM/TIM_BreakAndDeadtime`
  - `Projects/STM32F411RE-Nucleo/Examples_LL/TIM/TIM_InputCapture`

## Selected implementation basis

- selected official implementation basis:
  - existing ST-backed CMSIS target in `firmware/targets/stm32f411ceu6`
- why this basis was chosen:
  - it already uses official ST startup/system/header sources
  - it is the lowest-risk path for the first direct-observation GPIO proof
- official files or examples actually used:
  - `firmware/targets/stm32f411ceu6/provenance.md`
  - ST startup/system/CMSIS files recorded there
- implementation facts still unknown:
  - final UART behavior on the real board
  - final ADC behavior on the real board
  - whether the WeAct EEPROM footprint is populated

## Selected AEL methodology basis

- closest validated AEL methodology sources:
  - `stm32f103_gpio_signature`
- why these were chosen:
  - it is the closest proven direct-observation STM32 GPIO signature pattern
- methodology elements reused:
  - direct two-pin capture
  - fast/half-rate ratio check
  - operator-visible LED heartbeat
  - plan-level direct signal checks plus frequency-ratio relation
- methodology elements intentionally not reused:
  - STM32F103 register-level implementation
  - STM32F103 pin choices

## Pre-generation drift check

- family drift:
  - `STM32F1` to `STM32F4` register and clock model drift exists
- package/pinout drift:
  - board-specific WeAct breakout was used instead of generic family assumptions
- clock drift:
  - F411 startup/system path differs from F103 and is vendor-anchored
- peripheral-instance drift:
  - UART/SPI/ADC/TIM mappings were re-anchored from official F411 examples
- linker/memory drift:
  - F411 linker/startup is official-source-based
- bench/setup drift:
  - probe endpoint and fixed wiring were updated to real bench facts
- unresolved blockers:
  - none for the first GPIO signature round

## Tests attempted

| test | implementation basis | methodology basis | result | notes |
| --- | --- | --- | --- | --- |
| `stm32f411_gpio_signature` | `firmware/targets/stm32f411ceu6` using ST CMSIS/startup/system sources | `stm32f103_gpio_signature` | pass | First probe endpoint attempt at `192.168.2.102` was blocked in preflight. After correcting the probe instance to `192.168.2.103` and fixing the nested-build-dir Makefile issue, the live run passed as `2026-03-14_06-48-30_stm32f411ceu6_stm32f411_gpio_signature`. |

## Results summary

- passed:
  - `stm32f411_gpio_signature`
- failed:
  - none in this round
- partial:
  - first run attempt revealed the stale `.102` probe endpoint and the nested-build-dir Makefile gap
- blocked:
  - no remaining blockers for the GPIO signature path after the probe endpoint was corrected to `.103`

## Inferred assumptions

- inference:
  - the existing ST-backed F411 target is sufficient for the first direct GPIO signature round
  - why it was inferred:
    - startup/system/CMSIS provenance is already official-source anchored
  - confidence:
    - medium-high
  - how it should be verified:
    - run the first GPIO signature test on hardware

## Rejected paths

- rejected path:
  - immediately generating all F411 peripheral tests
  - why it was rejected:
    - violates the staged first-time bring-up rule
  - what evidence led to rejection:
    - first-time MCU support policy added earlier in this repo

## Lessons learned

- what succeeded:
  - the bench contract was frozen before code generation
- what failed:
  - the first attempt used an outdated probe endpoint (`192.168.2.102`) and failed preflight
  - the first corrected `.103` attempt exposed a build-system gap when using nested artifact directories
- what was learned:
  - direct-observation GPIO is still the safest first F411 validation step
  - the live bench probe instance for STM32F411 is `esp32jtag_stm32f411 @ 192.168.2.103:4242`
  - F411 target Makefiles must create nested object directories under custom build paths
- what should be written back into skills/workflows/specs:
  - first-round reports must separate bench-unreachable blocks from DUT/test failures

## Recommended next step

- next safest implementation step:
  - expand from the validated GPIO signature path into UART, ADC, SPI, and the shared-loopback family using the frozen F411 connection contract
- next safest validation step:
  - keep `esp32jtag_stm32f411 @ 192.168.2.103:4242` as the active probe endpoint
  - continue the staged peripheral bring-up sequence on live hardware
- user or bench facts still needed:
  - whether the F411 probe is powered and on the expected network
  - whether the EEPROM footprint is populated
