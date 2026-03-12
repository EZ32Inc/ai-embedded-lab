# Local Instrument Interface Meter Action Mapping v0.1

## Purpose

This note maps the current meter-backed verification path onto the bounded Local Instrument Interface action vocabulary.

It does not change runtime behavior.

## Current Meter Native Actions

The current bounded meter native actions are:

- `measure_digital`
- `measure_voltage`
- `stim_digital`

These are lower-layer actions.

## Current Verification Usage

Current ESP32-C6 meter-backed verification still runs above the lower layer.

At a high level:

- `uart.verify`
  - remains outside the lower layer
  - this is DUT/runtime observation, not a meter-native action
- `instrument.signature`
  - currently depends on meter-backed capture and comparison logic
  - comparison and pass/fail verdict remain above the lower layer

## Practical Mapping

The useful current conceptual mapping is:

- digital GPIO signature capture
  - lower-layer primitive: `measure_digital`
  - higher-layer logic:
    - expected-pattern comparison
    - transition checks
    - DUT verdict

- analog 3V3 check
  - lower-layer primitive: `measure_voltage`
  - higher-layer logic:
    - expected-range comparison
    - DUT verdict

- meter self-test or future stimulus workflows
  - lower-layer primitive: `stim_digital`
  - higher-layer logic:
    - orchestration
    - sequencing
    - comparison

## Important Boundary

What stays above the lower layer:

- verify-stage pass/fail
- signature match/mismatch
- degraded-instrument policy
- suite-level retry and reporting

What belongs in the lower layer:

- raw native measurement/stimulation actions
- status and doctor behavior
- capability metadata

## Conclusion

The meter native API is already a useful lower-layer shape.

The current repository should keep using it as:

- an additive native action vocabulary
- not as a direct replacement for higher-level verification logic
