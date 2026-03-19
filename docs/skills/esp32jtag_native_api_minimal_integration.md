# ESP32JTAG Native API Minimal Integration

## Purpose

Use this skill when `ESP32JTAG` already has a stable backend action package,
but still needs a first-class instrument-level interface model.

## Rule

Do not treat this as a backend rewrite.

Add only the instrument-level layer:

- identify
- get_capabilities
- get_status
- doctor

Keep action execution in `esp32_jtag backend`.

## Recommended Order

1. define the instrument model as `multi_capability_instrument`
2. implement `jtag_native_api` for metadata/status/doctor only
3. route control-native metadata calls through `native_api_dispatch`
4. expose the model in `instrument_view` and `instrument_doctor`
5. verify one real `ESP32JTAG` instance with `ael instruments doctor`

## Key Boundary

`jtag_native_api` owns:

- instrument identity
- capability-family reporting
- status
- doctor

`esp32_jtag backend` owns:

- flash
- reset
- debug execution
- gpio measure execution
- runtime transport

## Important Design Constraint

`ESP32JTAG` is not a single-purpose JTAG probe.

Model it as a multi-capability instrument with at least:

- debug remote capability
- reset/control capability
- capture/control capability

Do not compress it into a one-surface `jtag_probe` abstraction.

## Common Failure Mode

It is easy to break existing manifest-backed instrument views while adding a new
instance-backed native API path.

When `instrument_view` can resolve both a manifest id and an instance id, prefer
the manifest for manifest-backed instruments and only fall back to instance
resolution when no manifest exists.

## Why

This gives `ESP32JTAG` a named instrument identity in doctor/view surfaces
without destabilizing the already-working backend execution path.
