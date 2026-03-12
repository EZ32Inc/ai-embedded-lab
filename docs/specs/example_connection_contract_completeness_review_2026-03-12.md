# Example Connection Contract Completeness Review 2026-03-12

This document records the Round 2 completeness sweep for generated example
connection contracts.

It is a bounded review. It does not redefine the connection model.

## Purpose

Confirm whether current generated examples can answer normal connection
questions through formal repo surfaces, and identify which examples remain
blocked for runtime validation because of intentionally unbound external
connections.

## Review method

The authoritative retrieval path remains:

1. `inventory describe-test`
2. test plan
3. board profile
4. firmware source only for missing contract explanation

## Result

### Formally complete and suitable for normal connection retrieval

The following generated examples are formally complete for normal connection
retrieval:

- RP2040:
  - `uart_banner`
  - `spi_banner`
  - `i2c_banner`
- RP2350:
  - `gpio_signature`
  - `uart_banner`
- STM32F103:
  - `uart_banner`
  - `spi_banner`
  - `i2c_banner`
- ESP32-C6:
  - `uart_banner`
  - `spi_banner`
  - `i2c_banner`

For these examples, current formal surfaces answer:

- serial console, when relevant
- peripheral signals
- current control-instrument or instrument path
- board/profile-derived bench connections

### Formally complete but intentionally unbound for external analog stimulus

The following examples are formally complete, but still declare intentionally
undefined external analog input:

- `tests/plans/rp2040_adc_banner.json`
- `tests/plans/stm32f103_adc_banner.json`
- `tests/plans/esp32c6_adc_meter.json`

These are not missing contract data in the retrieval sense. They are bounded
examples whose external analog source has not yet been defined.

## Implication for runtime validation

### Good next candidates

Current strongest runtime-validation candidates remain:

- UART examples on RP2040
- UART examples on STM32F103

SPI and I2C examples may also become candidates when a specific bench-side
runtime expectation is chosen, but they are not the first priority.

### Deferred candidates

ADC examples should remain deferred for stronger runtime claims until a real
external analog-source contract is added.

ESP32-C6 generated examples should also remain conservative for runtime claims
when meter-side bench instability blocks live runs.

## Conclusion

The repo now has enough formal connection-contract structure for bounded
cross-family example generation.

The remaining limit is no longer retrieval ambiguity. It is selective bench
readiness and intentionally deferred external-input modeling.
