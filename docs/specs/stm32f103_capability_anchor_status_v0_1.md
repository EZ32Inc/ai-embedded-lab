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

### UART loopback self-check path
- status: `live-pass`
- meaning:
  - bounded generated unified-board UART execution proof
  - `PA9 -> PA10`
  - internal UART self-check on the unified fixture
  - result encoded onto `PA4`

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

### EXTI self-check path
- status: `live-pass`
- meaning:
  - bounded generated EXTI execution proof
  - `PA8 -> PB8`
  - internal EXTI self-check on the unified timing loopback
  - result encoded onto `PA4`

### Capture/timing self-check path
- status: `live-pass`
- meaning:
  - bounded generated capture/timing execution proof
  - `PA8 -> PB8`
  - internal timing/capture self-check on the unified timing loopback
  - result encoded onto `PA4`

## Accepted immediate next path
- stop and review before adding another capability path on this fixture
- current bounded `PA8 -> PB8` path set is now:
  - GPIO loopback
  - PWM
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
- `stm32f103_uart_loopback_banner`
- `stm32f103_adc_banner`
- `stm32f103_spi_banner`
- `stm32f103_pwm_banner`
- `stm32f103_gpio_loopback_banner`
- `stm32f103_exti_banner`
- `stm32f103_capture_banner`

### Design-confirmed / next to execute
- none required before the next anchor review

## What should happen next
- do a bounded STM32 capability-anchor review before adding the next capability path
- decide whether the next move should be:
  - one more self-check on the same fixture
  - or a new external-path / family direction
