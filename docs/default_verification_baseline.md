# Default Verification Baseline Anchor

This document records the currently stable baseline after the STM32 BMDA flash fix.

## Bound instrument instances

- `rp2040_pico` -> `esp32jtag_rp2040_lab`
  - endpoint: `192.168.2.63:4242`
- `stm32f103` -> `esp32jtag_stm32_golden`
  - endpoint: `192.168.2.98:4242`
- `stm32f401rct6` -> `esp32jtag_stm32_golden`
  - endpoint: `192.168.2.98:4242`

Instrument type:

- `esp32jtag`

## Expected evidence shape

- `esp32c6_golden_gpio`
  - `uart.verify`
  - `instrument.signature`
- `rp2040_golden_gpio_signature`
  - `gpio.signal`
- `stm32f103_golden_gpio_signature`
  - `gpio.signal`

## Repeatability results

- default verification: `10/10`
- STM32F401 golden GPIO: `10/10`
- STM32F103 golden GPIO: `10/10`

## Known-good run artifacts

- ESP32-C6 evidence:
  - `runs/2026-03-09_14-57-25_esp32c6_devkit_esp32c6_gpio_signature_with_meter/artifacts/evidence.json`
- RP2040 evidence:
  - `runs/2026-03-09_14-58-12_rp2040_pico_gpio_signature/artifacts/evidence.json`
- STM32F103 evidence:
  - `runs/2026-03-09_14-58-42_stm32f103_gpio_signature/artifacts/evidence.json`
