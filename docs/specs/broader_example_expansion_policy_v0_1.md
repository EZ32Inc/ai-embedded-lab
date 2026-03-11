# Broader Example Expansion Policy v0.1

## Purpose

Define how AEL should approach higher-risk example expansion areas after the current bounded UART/ADC/SPI/I2C batches.

This covers:

- USB examples
- first examples in new vendor families such as TI or NXP

## Current Position

The current repo is ready for bounded cross-family example expansion when:

- generation policy exists
- family guidance exists
- `inventory describe-test` answers connection questions formally
- `explain-stage --stage plan` resolves coherently
- build smoke passes

That is now true for the current RP2, STM32F103, and ESP32-C6 example batches.

## USB Policy

USB remains a separate higher-risk area.

Reasons:

- board sensitivity is higher
- host/device interaction assumptions are less uniform
- connection contracts usually need more than `serial_console` plus peripheral pins
- runtime validation is often less deterministic than GPIO/UART/ADC/SPI/I2C

Policy:

1. do not fold USB into the normal bounded peripheral batch by default
2. create a family-specific USB plan only when there is a clear bench/validation contract
3. require an explicit connection contract before calling the example ready

## New Vendor Family Policy

For a first MCU family such as TI or NXP:

1. create a family generation policy first
2. choose one bounded first example
3. keep provenance explicit
4. validate through:
   - `inventory describe-test`
   - `explain-stage --stage plan`
   - build smoke
5. only then use that result as the local reference for later expansion

## Working Rule

Broader expansion should stay:

- policy-first
- contract-first
- bounded

Do not treat "it compiles" as enough for USB or a first vendor-family example.

## Suggested Order

1. finish bounded same-family example batches
2. confirm connection contracts are formal enough
3. choose one higher-risk target area
4. add family/policy guidance before scaling it
