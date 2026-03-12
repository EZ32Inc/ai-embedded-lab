# Example Runtime Validation Candidate Set v0.1

## Purpose

This note records the first bounded runtime-validation candidate set for generated examples.

It is intentionally conservative.

## Selection Rule

The first runtime-validation batch should prefer examples that:

- already have a formal connection contract
- do not depend on undefined external analog stimulus
- match currently available bench connectivity
- can be validated with the least new bench setup work

## Current Candidate Review

### Strong candidate

- `esp32c6_uart_banner`

Why:

- formal connection contract is complete
- serial console is formally defined as `auto_usb_serial_jtag`
- current ESP32-C6 bench path is already exercised regularly
- no extra undefined analog source is required

### Deferred candidates

- `rp2040_uart_banner`
- `stm32f103_uart_banner`
- `rp2350_uart_banner`

Reason for deferral:

- generated examples are plan/build-valid
- but current runtime validation should wait for explicit confirmation of the intended host serial path on the current bench setup

### Not first-batch candidates

- ADC examples
  - external analog input contract remains formally unbound
- SPI/I2C examples
  - formally defined, but runtime bench value is lower than UART as a first proof point
- USB examples
  - explicitly deferred as a later higher-risk batch

## First Batch Decision

The first bounded runtime-validation batch should use:

- `esp32c6_uart_banner`

Optional second candidate later, after explicit bench confirmation:

- one of `rp2040_uart_banner` or `stm32f103_uart_banner`

## Exit Condition

This first runtime-validation batch is sufficient when:

- one generated example is proven live on bench
- the example catalog records that status conservatively
- the workflow for moving from build-valid to runtime-validated is documented
