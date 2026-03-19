# Generic Control Native API Review

Date: 2026-03-19

## Purpose

Review whether `control_instrument_native_api` should remain a first-class
runtime path now that `ESP32JTAG` has a dedicated `jtag_native_api`.

## Current State

`control_instrument_native_api` still exists and still provides:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `preflight_probe`
- `program_firmware`
- `capture_signature`
- `observe_gpio`

It is still used indirectly for:

- generic control-style helper actions
- compatibility in native dispatch
- some older tests and phase-2 routing assumptions

## What Has Changed

For `ESP32JTAG`, runtime identity and health reporting should now prefer:

- `jtag_native_api`

not:

- `control_instrument_native_api`

That is already true in:

- instrument view
- instrument doctor
- default verification runtime labeling

## Recommended Boundary

`control_instrument_native_api` should now be treated as:

- a generic compatibility/helper surface
- not the preferred instrument identity for `ESP32JTAG`

### Keep It For

- `program_firmware`
- `capture_signature`
- `observe_gpio`
- older tests that intentionally exercise the generic path
- any future non-family-specific control instrument fallback

### Do Not Use It As

- the preferred runtime label for `ESP32JTAG`
- the primary source of `ESP32JTAG` identity/status/doctor semantics

## Recommendation

Do not delete it yet.

Instead, treat it as a bounded legacy-compatible helper layer:

- useful
- still needed
- but no longer the canonical interface model for `ESP32JTAG`

## Practical Rule

When a path is specifically about `ESP32JTAG` as an instrument, prefer:

- `jtag_native_api`

When a path is explicitly generic or compatibility-oriented, using
`control_instrument_native_api` is still acceptable.
