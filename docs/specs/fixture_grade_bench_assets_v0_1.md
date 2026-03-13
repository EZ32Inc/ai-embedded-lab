## Fixture-Grade Bench Assets

Purpose:
- record the current stable working hardware setups that should be treated as long-lived regression anchors rather than temporary experiments

### Core default-verification fixtures

#### RP2040 GPIO golden fixture
- DUT: `rp2040_pico`
- path: `rp2040_gpio_signature`
- control instrument: `esp32jtag_rp2040_lab @ 192.168.2.63:4242`
- role:
  - core default baseline worker
  - secondary family baseline anchor

#### STM32 GPIO golden fixture
- DUT: `stm32f103`
- path: `stm32f103_gpio_signature`
- control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- role:
  - core default baseline worker
  - primary sample-board capability anchor

#### STM32 UART bridge fixture
- DUT: `stm32f103_uart`
- path: `stm32f103_uart_bridge_banner`
- control instrument: `esp32jtag_stm32_uart @ 192.168.2.99:4242`
- UART instrument: `usb_uart_bridge_daemon @ 192.168.2.78:8767`
- role:
  - core default baseline worker
  - bounded remote USB-UART execution proof

#### ESP32-C6 meter fixture
- DUT: `esp32c6_devkit`
- path: `esp32c6_golden_gpio`
- instrument: `esp32s3_dev_c_meter`
- role:
  - core default baseline worker
  - meter-backed execution anchor
- note:
  - still bench-sensitive and should be treated as a known-noisier fixture

### Extended STM32 capability fixture

#### STM32 ADC loopback fixture
- DUT: `stm32f103`
- path: `stm32f103_adc_banner`
- control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- loopback wiring:
  - `PA1 -> PA0`
- role:
  - bounded generated ADC execution proof
  - capability-extension anchor on the primary STM32 sample board

### Anchor designation

- core default baseline anchor:
  - the 4-worker `verify-default` suite
- primary sample-board capability anchor:
  - `stm32f103`
- secondary family baseline anchor:
  - `rp2040_pico`
