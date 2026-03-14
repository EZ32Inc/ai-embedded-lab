# STM32F103 Capability Anchor Status v0.1

## Current board role
- primary sample-board capability anchor for bounded capability-demo expansion
- central index of record for the completed bounded STM32F103 self-check phase

## Phase state
- the current bounded STM32F103 self-check phase is complete

## Capability index

| Demo/path name | Status | Proof method | Result record | Closeout |
| --- | --- | --- | --- | --- |
| `stm32f103_gpio_signature` | `repeat-pass` | external GPIO signature observed on the STM32 golden path | baseline run history under `runs/...` | documented as the stable core STM32 baseline path in this anchor note |
| `stm32f103_uart_banner` | `live-pass` | USB-UART bridge path with bounded UART banner verification | bridge run history under `runs/...` | bridge path closeout/history already recorded in the existing UART bridge notes |
| `stm32f103_uart_loopback_banner` | `live-pass` | `PA9 -> PA10` internal UART loopback, result encoded onto `PA4` | [stm32f103_uart_loopback_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_uart_loopback_self_check_result_2026-03-13.json) | [stm32f103_uart_loopback_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_uart_loopback_self_check_closeout_v0_1.md) |
| `stm32f103_adc_banner` | `repeat-pass` | `PA1 -> PA0` ADC closed-loop, ADC-validated result encoded onto `PA4` | [stm32f103_adc_loopback_health_note_2026-03-12.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_adc_loopback_health_note_2026-03-12.md) | [stm32f103_adc_loopback_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_adc_loopback_closeout_v0_1.md) |
| `stm32f103_spi_banner` | `live-pass` | `PA7 -> PA6` internal SPI loopback on `PA5/PA6/PA7`, result encoded onto `PA4` | [stm32f103_spi_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_spi_self_check_result_2026-03-13.json) | [stm32f103_spi_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_spi_self_check_closeout_v0_1.md) |
| `stm32f103_pwm_banner` | `live-pass` | `PA8 -> PB8` internal PWM loopback, result encoded onto `PA4` | [stm32f103_pwm_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_pwm_self_check_result_2026-03-13.json) | [stm32f103_pwm_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_pwm_self_check_closeout_v0_1.md) |
| `stm32f103_gpio_loopback_banner` | `live-pass` | `PA8 -> PB8` internal GPIO loopback, result encoded onto `PA4` | [stm32f103_gpio_loopback_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_gpio_loopback_self_check_result_2026-03-13.json) | [stm32f103_gpio_loopback_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_gpio_loopback_self_check_closeout_v0_1.md) |
| `stm32f103_exti_banner` | `live-pass` | `PA8 -> PB8` internal EXTI self-check, result encoded onto `PA4` | [stm32f103_exti_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_exti_self_check_result_2026-03-13.json) | [stm32f103_exti_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_exti_self_check_closeout_v0_1.md) |
| `stm32f103_capture_banner` | `live-pass` | `PA8 -> PB8` internal capture/timing self-check, result encoded onto `PA4` | [stm32f103_capture_self_check_result_2026-03-13.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_capture_self_check_result_2026-03-13.json) | [stm32f103_capture_self_check_closeout_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32f103_capture_self_check_closeout_v0_1.md) |

## Summary
- GPIO golden remains the stable core STM32 baseline path
- UART is now proven in two bounded forms:
  - USB-UART bridge path
  - unified-board `PA9 -> PA10` loopback self-check
- the unified-board self-check set is proven for:
  - ADC
  - SPI
  - PWM
  - GPIO loopback
  - EXTI
  - capture/timing

## Accepted immediate next path
- stop and review before adding another capability path on this fixture
- current bounded `PA8 -> PB8` path set is now:
  - GPIO loopback
  - PWM
  - EXTI
  - capture/timing

## Proposed second-wave path
- `PA8 -> PB8`
- intended for:
  - GPIO
  - EXTI
  - capture/timing-class demos

## Reserved paths
- I2C:
  - reserved/exploratory only for now

## Status boundary

- all currently accepted bounded STM32F103 self-check paths listed above are `live-pass` or `repeat-pass`
- no additional STM32F103 self-check path is required before the next anchor review or next-board migration decision

## What should happen next
- use this note as the reference index during method-layer refinement
- preserve the completed STM32F103 phase as a stop point
- decide the next board migration step only after the method-layer refinement pass is complete
