# default_verification_review_003

## Question

What is currently covered and is the default verification baseline healthy?

## Approved Answer Draft

Current default verification baseline:

- `esp32c6_gpio_signature_with_meter`
  - board: `esp32c6_devkit`
  - validation style: meter-backed GPIO golden test
  - current run result: `FAIL` at flash because no serial port was available
- `rp2040_gpio_signature`
  - board: `rp2040_pico`
  - validation style: probe-based GPIO signature test
  - current run result: `PASS`
- `stm32f103_gpio_signature`
  - board: `stm32f103_gpio`
  - validation style: probe-based GPIO signature test
  - current run result: `PASS`
- `stm32f103_uart_banner`
  - board: `stm32f103_uart`
  - validation style: UART banner plus GPIO proof
  - current run result: `PASS`
- `stm32f411_gpio_signature`
  - board: `stm32f411ceu6`
  - validation style: probe-based GPIO signature test
  - current run result: `PASS`

Current coverage summary:

- the current configured default baseline has five DUT-backed steps
- STM32F411 is now included through the representative low-risk baseline step `stm32f411_gpio_signature`
- in the latest live run, RP2040, STM32F103 GPIO, STM32F103 UART, and STM32F411 all passed

Baseline health assessment:

- the baseline is not fully healthy at the moment because the ESP32-C6 step still has an active flash/serial-path problem
- the STM32F411 default-verification integration itself is healthy and passed in the live baseline flow

Important caveats:

- this reflects the current default baseline and current bench state, not every AEL path
- the current unhealthy point is the ESP32-C6 flash serial path, not the new STM32F411 step
- STM32F411 is intentionally represented by one low-risk baseline test in default verification, not the full eight-test board suite

## Retrieval Path

- `python3 -m ael inventory list`
- `python3 -m ael verify-default run`
