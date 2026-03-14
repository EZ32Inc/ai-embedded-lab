# describe_test_stm32f411_001

Current `stm32f411_gpio_signature` setup from inventory is:

- board: `stm32f411ceu6`
- control instrument: `esp32jtag_stm32f411 @ 192.168.2.103:4242`
- connections:
  - `SWD -> P3`
  - `RESET -> NC`
  - `PA2 -> P0.0`
  - `PA3 -> P0.1`
  - `PB13 -> P0.2`
  - `PC13 -> LED`
  - `GND -> probe GND`

What it tests:

- direct signal check on `PA2` via `P0.0`
- direct signal check on `PA3` via `P0.1`
- frequency-ratio check between the fast `PA2` waveform and the half-rate `PA3` waveform

Current validation scope:

- this is the STM32F411 GPIO signature baseline
- it proves flash/run plus the two-signal GPIO signature contract
- it does not by itself prove UART, ADC, SPI, PWM, EXTI, or capture
