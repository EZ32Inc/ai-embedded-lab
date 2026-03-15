# stm32f401rct6

STM32F401RCT6 — 64-pin LQFP, 256KB flash, 64KB RAM, Cortex-M4 @ 16MHz HSI.

## Bench Wiring

| DUT pin | Instrument (ESP32JTAG) | Role |
|---------|------------------------|------|
| PA2     | P0.0                   | Primary status/signature signal |
| PA3     | P0.1                   | Secondary signature (half-rate) |
| PB13    | P0.2                   | SPI2 SCK auxiliary observation |
| PC13    | LED                    | Heartbeat LED |
| GND     | probe GND              | Common ground |
| SWDIO/SWDCLK | P3            | Debug / flash (SWD) |
| RESET   | NC                     | Not connected |

## Board Loopbacks (per experiment)

| Experiment | Short on DUT board |
|---|---|
| UART loopback | PA9 → PA10 |
| SPI loopback  | PB15 → PB14 |
| ADC loopback  | PB1 → PB0 |
| Capture / EXTI / GPIO loopback / PWM | PA8 → PA6 |

## Experiment Suite (8 tests)

1. `stm32f401_gpio_signature` — PA2 ~25Hz, PA3 ~12.5Hz, ratio 2:1
2. `stm32f401_uart_loopback_banner` — USART1 PA9/PA10, result on PA2
3. `stm32f401_spi_banner` — SPI2 PB13/14/15 loopback, result on PA2
4. `stm32f401_adc_banner` — ADC1_IN8 PB0 with PB1 source, result on PA2
5. `stm32f401_capture_banner` — TIM1→TIM3 capture PA8→PA6, result on PA2
6. `stm32f401_exti_banner` — EXTI PA6 edge count via PA8→PA6, result on PA2
7. `stm32f401_gpio_loopback_banner` — GPIO read-back PA8→PA6, result on PA2
8. `stm32f401_pwm_banner` — TIM1 PWM PA8→PA6 sense, result on PA2

## Instrument

`esp32jtag_stm32_golden` at `192.168.2.98`, GDB port 4242.

## Firmware

All firmware is bare-metal CMSIS, 16MHz HSI, no PLL.
- GPIO signature: `firmware/targets/stm32f401rct6/`
- Banner experiments: `firmware/targets/stm32f401_<name>/`

## Notes

- Same F4 peripheral register map as F411 — SPI2, USART1, TIM1, TIM3, ADC1 pin assignments identical.
- F401RCT6 uses `stm32f401xc.h` (xC = 256KB flash variant).
- Do not copy F1 GPIO init code — F4 uses MODER/AFR, F1 uses AFIO_MAPR.
