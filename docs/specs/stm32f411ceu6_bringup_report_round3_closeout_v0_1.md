# STM32F411CEU6 Bring-Up Report Round 3 Closeout v0.1

## Scope

- close out the first STM32F411 bring-up cycle after the SPI issue was resolved
- remove temporary SPI diagnostics
- confirm the production F411 suite still passes after cleanup
- integrate the F411 DUT into the live AEL inventory/default-verification layer

## Final bench contract used

- control instrument:
  - `esp32jtag_stm32f411 @ 192.168.2.103:4242`
- fixed wiring:
  - `SWD -> P3`
  - `RESET -> NC`
  - `GND -> probe GND`
  - `PA2 -> P0.0`
  - `PA3 -> P0.1`
  - `PB13 -> P0.2`
  - `PC13 -> LED`
- jumpers:
  - ADC: `PB1 -> PB0`
  - shared loopback: `PA8 -> PA6`
  - UART loopback: `PA9 -> PA10`
  - SPI loopback: `PB15 -> PB14`

## Cleanup completed

- removed temporary SPI debug targets:
  - `stm32f411_pb13_gpio_probe`
  - `stm32f411_spi_clock_probe`
- removed temporary SPI debug plans:
  - `zz_tmp_stm32f411_pb13_gpio_probe`
  - `zz_tmp_stm32f411_spi_clock_probe`
  - `zz_tmp_stm32f411_spi_pa3_diag`
- restored `firmware/targets/stm32f411_spi/main.c` to the production self-check form
- kept the SPI proof window aligned to the measured F411 range:
  - `15..35 Hz`

## Full suite rerun

All eight STM32F411 tests passed on live hardware:

| test | run id | result |
| --- | --- | --- |
| `stm32f411_gpio_signature` | `2026-03-14_09-22-08_stm32f411ceu6_stm32f411_gpio_signature` | pass |
| `stm32f411_uart_loopback_banner` | `2026-03-14_09-22-45_stm32f411ceu6_stm32f411_uart_loopback_banner` | pass |
| `stm32f411_adc_banner` | `2026-03-14_09-23-10_stm32f411ceu6_stm32f411_adc_banner` | pass |
| `stm32f411_spi_banner` | `2026-03-14_09-23-37_stm32f411ceu6_stm32f411_spi_banner` | pass |
| `stm32f411_gpio_loopback_banner` | `2026-03-14_09-24-08_stm32f411ceu6_stm32f411_gpio_loopback_banner` | pass |
| `stm32f411_pwm_banner` | `2026-03-14_09-24-35_stm32f411ceu6_stm32f411_pwm_banner` | pass |
| `stm32f411_exti_banner` | `2026-03-14_09-24-58_stm32f411ceu6_stm32f411_exti_banner` | pass |
| `stm32f411_capture_banner` | `2026-03-14_09-25-25_stm32f411ceu6_stm32f411_capture_banner` | pass |

## Inventory/default-verification integration

- added DUT manifest:
  - `assets_golden/duts/stm32f411ceu6/manifest.yaml`
- added DUT notes:
  - `assets_golden/duts/stm32f411ceu6/docs.md`
- added smoke pack:
  - `packs/smoke_stm32f411.json`
- added `stm32f411_gpio_signature` to:
  - `configs/default_verification_setting.yaml`

## Latest default-verification evidence

- latest default-verification run with F411 included:
  - `2026-03-14_09-29-06_stm32f411ceu6_stm32f411_gpio_signature` -> `PASS`
- suite nuance:
  - the same run still hit an unrelated ESP32-C6 flash/serial-path problem
  - F411 itself integrated cleanly into the baseline flow

## Lessons learned

- the original SPI blocker was a physical solder/connectivity fault on `PB13/PB14`
- temporary direct pin probes were the fastest way to separate bench faults from firmware/peripheral faults
- F411 proof timing matches the broader measured self-check cadence near `24 Hz`, not the original F103-like `50 Hz` assumption
- once the physical path was fixed, the official-source-based F411 SPI implementation worked without deeper register-level redesign

## Result

- first-pass STM32F411 bring-up is complete
- the F411 DUT is now:
  - present in inventory
  - validated across the baseline GPIO signature and the first self-check suite
  - integrated into the live default-verification configuration as a DUT-backed test
