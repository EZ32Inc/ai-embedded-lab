# Example Runtime Readiness Round 1 Checkpoint v0.1

This document records the first bounded runtime-readiness classification pass
for generated examples.

## Scope

Round 1 focused on:

- defining runtime-readiness categories
- adding readiness tracking to the example catalog
- classifying the current generated example set

It did not claim new runtime validation.

## Classification result

### Blocked by missing bench setup

- `tests/plans/rp2040_uart_banner.json`
- `tests/plans/rp2350_uart_banner.json`
- `tests/plans/rp2040_spi_banner.json`
- `tests/plans/rp2040_i2c_banner.json`
- `tests/plans/stm32f103_uart_banner.json`
- `tests/plans/stm32f103_spi_banner.json`
- `tests/plans/stm32f103_i2c_banner.json`
- `tests/plans/rp2350_gpio_signature.json`

These examples are formally complete enough for retrieval, but the required
runtime bench path is not provisioned or confirmed for meaningful live
validation today.

### Blocked by unbound external input

- `tests/plans/rp2040_adc_banner.json`
- `tests/plans/stm32f103_adc_banner.json`
- `tests/plans/esp32c6_adc_meter.json`

These examples are formally complete, but the external analog source remains
intentionally undefined.

### Blocked by unstable bench path

- `tests/plans/esp32c6_uart_banner.json`
- `tests/plans/esp32c6_spi_banner.json`
- `tests/plans/esp32c6_i2c_banner.json`

These examples are formally runnable, but the current meter-backed ESP32-C6
bench path remains unstable enough that runtime claims should stay conservative.

## Conclusion

The main current limit is no longer missing formal connection metadata.

The main limit is runtime readiness:

- missing UART/runtime bench provisioning on RP2 and STM32 generated examples
- intentionally unbound external analog inputs on ADC examples
- unstable current bench path for ESP32-C6 generated examples
