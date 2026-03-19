# ESP32 Meter Instrument Interface Follow-Up

Date: 2026-03-19

## Purpose

Review what still remains to make `ESP32-S3 meter` feel as complete at the
instrument-interface level as `ESP32JTAG`.

## Current State

`ESP32-S3 meter` already has:

- a unified backend package for action execution
- a native API used by runtime consumers
- explicit instrument manifest metadata
- real live runtime validation on a meter-backed path

Current active surface:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `measure_digital`
- `measure_voltage`
- `stim_digital`

## What Is Still Weaker Than `ESP32JTAG`

1. Instrument identity is less explicit.
- `meter_native_api` still reports a simpler `device_type = meter`
- it does not yet have the same kind of explicit instrument-family framing that
  `ESP32JTAG` now has

2. Status domains are not explicitly normalized.
- `get_status` currently reports reachability
- it does not yet split health into stable runtime domains the way
  `ESP32JTAG` now does

3. Lifecycle boundary is implicit.
- meter status/doctor/provision boundaries are described in docs
- but the native interface profile does not yet carry an explicit lifecycle
  ownership declaration

4. Runtime presentation is adequate, but less intentionally modeled.
- the meter already shows up as its own instrument
- but there is less explicit "instrument API completeness" language around it

## What Does Not Need To Change Immediately

- action execution ownership
- backend package shape
- runtime consumer bridge through `meter_native_api`

Those parts are already in a good state.

## Recommended Next Step

If follow-on work is needed, it should mirror the `ESP32JTAG` pattern, but only
for metadata/status/doctor quality:

1. make `instrument_family` explicit
2. define stable meter status domains
3. state lifecycle ownership in the native profile
4. keep action execution where it is

## Recommendation

Do **not** start by moving more code.

Start by clarifying the meter instrument-interface model the same way
`ESP32JTAG` was clarified:

- identity
- status domains
- lifecycle boundary
- runtime presentation

That is the smallest high-value follow-up.
