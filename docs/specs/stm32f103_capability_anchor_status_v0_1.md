# STM32F103 Capability Anchor Status v0.1

## Current board role
- primary sample-board capability anchor for bounded capability-demo expansion

## Already-proven paths

### GPIO golden
- status: `repeat-pass`
- meaning:
  - stable core STM32 baseline path

### UART bridge path
- status: `live-pass`
- meaning:
  - bounded generated UART execution proof
  - proven locally, daemonized same-host, and remote-host through the USB-UART bridge path

### ADC closed-loop path
- status: `repeat-pass`
- meaning:
  - bounded generated ADC execution proof
  - `PA1 -> PA0`
  - ADC-validated result encoded onto `PA4`
  - repeated `5/5 PASS`

### SPI self-check path
- status: `live-pass`
- meaning:
  - bounded generated SPI execution proof
  - `PA7 -> PA6`
  - internal SPI self-check on `PA5/PA6/PA7`
  - result encoded onto `PA4`

### PWM self-check path
- status: `live-pass`
- meaning:
  - bounded generated PWM execution proof
  - `PA8 -> PB8`
  - internal PWM self-check on the unified timing loopback
  - result encoded onto `PA4`

### GPIO loopback self-check path
- status: `live-pass`
- meaning:
  - bounded generated GPIO loopback execution proof
  - `PA8 -> PB8`
  - internal GPIO self-check on the unified timing loopback
  - result encoded onto `PA4`

## Accepted immediate next path
- `PA8 -> PB8` bounded digital timing path follow-on
- expected bounded shape:
  - reuse the same output/input pair on the same board
  - result encoded onto `PA4`
  - external observation remains on `PA4`
  - next sub-path should be one of:
    - GPIO self-check
    - EXTI
    - capture/timing

## Proposed second-wave path
- `PA8 -> PB8`
- intended for:
  - GPIO
  - EXTI
  - capture/timing-class demos

## Reserved paths
- I2C:
  - reserved/exploratory only for now

## Real-pass vs design-confirmed

### Real-pass / repeat-pass
- `stm32f103_golden_gpio_signature`
- `stm32f103_uart_bridge_banner`
- `stm32f103_adc_banner`
- `stm32f103_spi_banner`
- `stm32f103_pwm_banner`
- `stm32f103_gpio_loopback_banner`

### Design-confirmed / next to execute
- bounded STM32 `PA8 -> PB8` timing/self-check follow-on path:
  - EXTI
  - capture/timing

## What should happen next
- use the unified fixture to implement the next bounded `PA8 -> PB8` timing/self-check follow-on path
- keep the scope to:
  - one blocker
  - one path
  - one proof
