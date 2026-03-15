# STM32F411CEU6 (WeAct Black Pill V2.0)

**MCU:** STM32F411CEU6 — Cortex-M4, 100 MHz (16 MHz HSI default), 512 KB flash, 128 KB RAM, 48-pin UFQFPN
**Family:** STM32F4
**Status:** verified
**Verification date:** 2026-03-14

---

## Verification Suite

Suite name: `stm32f411_basic`
Pack: `packs/smoke_stm32f411.json`
Result: **8 / 8 PASS** (sequential run)

| # | Experiment | Test Plan | Loopback |
|---|-----------|-----------|---------|
| 1 | GPIO signature | stm32f411_gpio_signature | — |
| 2 | UART loopback banner | stm32f411_uart_loopback_banner | PA9 → PA10 |
| 3 | SPI banner | stm32f411_spi_banner | PB15 → PB14 |
| 4 | ADC banner | stm32f411_adc_banner | PB1 → PB0 |
| 5 | TIM capture banner | stm32f411_capture_banner | PA8 → PA6 |
| 6 | EXTI banner | stm32f411_exti_banner | PA8 → PA6 |
| 7 | GPIO loopback banner | stm32f411_gpio_loopback_banner | PA8 → PA6 |
| 8 | PWM banner | stm32f411_pwm_banner | PA8 → PA6 |

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
Header: `stm32f411xe.h`.

- GPIO signature: `firmware/targets/stm32f411ceu6/`
- Banner experiments: `firmware/targets/stm32f411_<name>/`

---

## Notes

- WeAct Black Pill V2.0 form factor.
- Same F4 peripheral register map as STM32F401 — SPI2, USART1, TIM1, TIM3, ADC1 pin assignments identical.
- First reference implementation for the STM32F4 family in AEL.
