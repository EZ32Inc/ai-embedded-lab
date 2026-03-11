# USB Example Generation Readiness v0.1

This note records the current AEL position on USB example generation after the
first bounded cross-family example expansion batches.

## Current conclusion

USB should remain a separate later batch.

It should not be grouped into the first broad example-expansion pass with:

- UART
- ADC
- SPI

## Why USB is different

USB examples are usually more sensitive to:

- exact board wiring and connector path
- host/device role assumptions
- descriptor and enumeration timing
- reset/boot timing
- serial-console interactions on USB-capable MCUs
- bench-side observation and validation strategy

Those constraints are stronger than for the current bounded UART/ADC/SPI paths.

## Family-specific implications

### ESP32-family

USB capability differs significantly across family members and board variants.
USB Serial JTAG, native USB device, and external UART paths are not equivalent.

### RP2-family

USB is often tied directly to the main console path and board power/enumeration
assumptions. That raises the risk of mixing validation transport with the
example’s peripheral behavior.

### STM32-family

USB support varies substantially by device line, package, clock setup, and
board-level PHY/connector assumptions. It is a poor first expansion target
compared with UART/ADC/SPI.

## Preconditions before USB expansion

Before starting a USB example batch, AEL should have:

1. stable non-USB example generation for the target family
2. clear board-level USB capability and wiring facts
3. a validation strategy that does not confuse transport with DUT behavior
4. bounded provenance rules for the USB example source basis

## Current recommendation

Proceed with:

- UART
- ADC
- SPI

across selected families first.

Reassess USB only after those examples are generated, plan-validated, and build
validated cleanly.
