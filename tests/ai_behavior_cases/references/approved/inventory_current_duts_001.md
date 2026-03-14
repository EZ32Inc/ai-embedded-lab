# inventory_current_duts_001

## Question

What DUTs and tests do we currently have?

## Approved Answer Draft

Current DUTs and tests:

- esp32c3_devkit
  - esp32c3_gpio_signature
  - esp32c3_gpio_signature_with_meter
- esp32c6_devkit
  - esp32c6_gpio_signature
  - esp32c6_gpio_signature_with_meter
- esp32s3_devkit
  - esp32s3_gpio_signature
  - esp32s3_gpio_signature_with_meter
- rp2040_pico
  - blink_gpio
  - rp2040_gpio_signature
  - recovery_demo_signal_fail_after_recovery
  - recovery_demo_signal_fail_first
  - recovery_demo_uart_fail_first
- stm32f103_gpio
  - stm32f103_gpio_signature
- stm32f103_uart
  - stm32f103_uart_banner
- stm32f401rct6
  - stm32f401_gpio_signature
  - stm32f401_gpio_smoke
  - stm32f401_led_blink
- stm32f411ceu6
  - stm32f411_adc_banner
  - stm32f411_capture_banner
  - stm32f411_exti_banner
  - stm32f411_gpio_loopback_banner
  - stm32f411_gpio_signature
  - stm32f411_pwm_banner
  - stm32f411_spi_banner
  - stm32f411_uart_loopback_banner

MCUs with tests:
- esp32c3
- esp32c6
- esp32s3
- rp2040
- stm32f103c8t6
- stm32f401rct6
- stm32f411ceu6

## Retrieval Path

- `python3 -m ael inventory list`
