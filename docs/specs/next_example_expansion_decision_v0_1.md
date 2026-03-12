# Next Example Expansion Decision v0.1

This note records the current bounded decision after the first generated-example
runtime-validation governance pass.

## Decision

The next generated-example expansion work should prioritize:

1. bounded runtime validation of UART examples on RP2040 and STM32F103
2. only after that, selective runtime validation of other generated examples
3. defer USB and new-vendor family expansion

## Why

### RP2040 and STM32F103 are the least blocked current paths

- their default verification paths are stable enough for repeated use
- their generated UART examples are formally complete
- they do not currently depend on the unstable ESP32-C6 meter bench path

### ESP32-C6 remains useful but should stay conservative

ESP32-C6 generated examples remain valid generation examples, but live
runtime-validation claims should remain conservative while current meter-backed
bench instability continues to block or distort attempts.

### ADC examples are not the next validation target

ADC examples are formally complete, but several still intentionally leave the
external analog source undefined. That makes them weaker candidates for the
next runtime-validation batch.

### USB remains a separate higher-risk expansion

USB should remain a separate decision and should not be mixed into the current
bounded validation path.

## Recommended immediate next batch

1. choose one RP2040 UART example and one STM32F103 UART example
2. run staged validation:
   - `inventory describe-test`
   - `explain-stage --stage plan`
   - live `run`
3. update the example catalog conservatively from the result

## Out of scope for this decision

- broad USB example generation
- broad new-vendor family generation
- broad runtime validation across all generated examples at once
