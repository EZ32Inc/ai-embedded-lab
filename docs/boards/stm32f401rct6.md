# STM32F401RCT6

**MCU:** STM32F401RCT6 — Cortex-M4, 84 MHz (16 MHz HSI default), 256 KB flash, 64 KB RAM, 64-pin LQFP
**Family:** STM32F4
**Status:** verified
**Verification date:** 2026-03-15

---

## Verification Suite

Suite name: `stm32f401_basic`
Pack: `packs/smoke_stm32f401.json`
Result: **8 / 8 PASS** (sequential run)

| # | Experiment | Test Plan | Loopback |
|---|-----------|-----------|---------|
| 1 | GPIO signature | stm32f401_gpio_signature | — |
| 2 | UART loopback banner | stm32f401_uart_loopback_banner | PA9 → PA10 |
| 3 | SPI banner | stm32f401_spi_banner | PB15 → PB14 |
| 4 | ADC banner | stm32f401_adc_banner | PB1 → PB0 |
| 5 | TIM capture banner | stm32f401_capture_banner | PA8 → PA6 |
| 6 | EXTI banner | stm32f401_exti_banner | PA8 → PA6 |
| 7 | GPIO loopback banner | stm32f401_gpio_loopback_banner | PA8 → PA6 |
| 8 | PWM banner | stm32f401_pwm_banner | PA8 → PA6 |

### Legacy Suite Status

The pack above is the preserved pre-Rule-B golden pack for STM32F401RCT6.
It remains a valid runnable baseline and is still expected to pass `8 / 8`.

### Rule-B Suite Status

Rule-B migration for STM32F401RCT6 starts from a separate Stage 0 LED blink
truth-layer test so the preserved legacy pack is not disturbed.

Stage 0 pack: `packs/stm32f401rct6_stage0.json`
Stage 0 test: `tests/plans/stm32f401rct6_pc13_blinky_visual.json`
Stage 0 mailbox pack: `packs/stm32f401rct6_stage0_mailbox.json`
Stage 0 mailbox test: `tests/plans/stm32f401rct6_minimal_runtime_mailbox.json`

Current policy:
- keep `packs/smoke_stm32f401.json` as the preserved legacy golden pack
- add the new Rule-B suite in parallel, stage by stage
- do not replace the preserved legacy pack until the newer suite is mature and re-validated

---

## Bench Wiring

| DUT pin | Instrument (ESP32JTAG) | Role |
|---------|------------------------|------|
| PA2 | P0.0 | Primary status / signature signal |
| PA3 | P0.1 | Secondary signature (half-rate) |
| PB13 | P0.2 | SPI2 SCK auxiliary observation |
| PC13 | LED | Heartbeat LED |
| GND | probe GND | Common ground |
| SWDIO / SWDCLK | P3 | Debug / flash (SWD) |
| RESET | NC | Not connected |

Instrument: `esp32jtag_stm32_golden` at `192.168.2.98`, GDB port 4242.

---

## Board-side Loopbacks (per experiment)

| Experiment | Short on DUT board |
|---|---|
| UART loopback | PA9 → PA10 |
| SPI loopback | PB15 → PB14 |
| ADC loopback | PB1 → PB0 |
| Capture / EXTI / GPIO loopback / PWM | PA8 → PA6 |

---

## Firmware

All firmware is bare-metal CMSIS, 16 MHz HSI, no PLL.
Header: `stm32f401xc.h` (xC = 256 KB flash variant).

- GPIO signature: `firmware/targets/stm32f401rct6/`
- Banner experiments: `firmware/targets/stm32f401_<name>/`

---

## Notes

- Same F4 peripheral register map as STM32F411 — SPI2, USART1, TIM1, TIM3, ADC1 pin assignments identical.
- Do not copy F1 GPIO init code — F4 uses MODER/AFR, F1 uses AFIO_MAPR.
- Second reference implementation for the STM32F4 family alongside STM32F411CEU6.
