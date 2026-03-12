# Local Instrument Interface Phase 2 Stop Boundary

## Purpose

Record the exact stop boundary for Phase 2 so the repo does not drift into a
broader instrument/runtime migration without opening a new phase explicitly.

## What Phase 2 Completed

For the three default-verification paths:

- `rp2040_golden_gpio_signature`
- `stm32f103_golden_gpio_signature`
- `esp32c6_golden_gpio`

the required instrument-touching runtime interactions now route through:

```text
verification/default-verification runtime
→ Local Instrument Interface
→ instrument native API
→ real instrument implementation
```

In bounded Phase 2 terms, this includes:

- RP2040:
  - preflight probe interaction
  - firmware load/program path used by default verification
  - verification-time signature capture
- STM32F103:
  - preflight probe interaction
  - firmware load/program path used by default verification
  - verification-time signature capture
- ESP32-C6:
  - meter-side status/reachability access used by the current runtime
  - digital measurement
  - voltage measurement

## What Phase 2 Explicitly Did Not Attempt

Phase 2 did not attempt:

- broad control-instrument redesign
- universal migration of all run/check paths
- broad flashing/debug stack redesign outside what the three default tests
  require
- universal meter/runtime normalization
- cloud registration/session runtime

## Future Work That Is Not Phase 2

The following should be treated as future phases:

- broader control-instrument unification
- migration of non-default-verification flows to the Local Instrument Interface
- broader instrument-family runtime migration
- cloud-facing registration/session implementation

## Working Rule

If a future batch touches instrument/runtime behavior outside the three default
verification paths above, it should not be described as Phase 2 continuation.
It should be opened and reviewed as a new phase.
