# stm32f411ceu6

Wiring expectations:
- SWD via ESP32JTAG `P3`
- `PA2 -> P0.0`
- `PA3 -> P0.1`
- `PB13 -> P0.2`
- LED on `PC13`

Reusable jumpers:
- ADC: `PB1 -> PB0`
- shared loopback: `PA8 -> PA6`
- UART loopback: `PA9 -> PA10`
- SPI loopback: `PB15 -> PB14`

Notes:
- Board target is `STM32F411CEU6 WeAct Black Pill V2.0`.
- Uses control instrument instance `esp32jtag_stm32f411`.
- GPIO signature baseline and the first self-check suite are validated on real hardware.
