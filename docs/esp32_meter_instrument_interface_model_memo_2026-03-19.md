# ESP32 Meter Instrument Interface Model Memo

Date: 2026-03-19

## Purpose

Define the instrument-level interface model for `ESP32-S3 meter` so it can be
described as cleanly as `ESP32JTAG`, without forcing unnecessary symmetry.

## 1. Instrument Identity

`ESP32-S3 meter` should be modeled as:

- `instrument_family = esp32_meter`
- `device_type = measurement_and_stimulus_instrument`
- `instrument_role = external_instrument`

It is not a generic probe and it is not a multi-capability debug instrument in
the `ESP32JTAG` sense.

Its core identity is:

- digital measurement
- analog voltage measurement
- digital stimulation

## 2. Minimum Standard Interface Surface

The minimum instrument-level surface should contain:

### Metadata

- `identify`
- `get_capabilities`

### Health / Status

- `get_status`
- `doctor`

### Actions

- `measure_digital`
- `measure_voltage`
- `stim_digital`

## 3. What Should Be Symmetric With `ESP32JTAG`

These should be symmetric:

- explicit `instrument_family`
- explicit ownership boundary
- explicit status/doctor model
- explicit runtime presentation in view/doctor/CLI

## 4. What Should Not Be Forced Symmetric

These do not need to match `ESP32JTAG`:

- action set
- capability families
- transport shape
- subsystem breakdown depth

`ESP32 meter` is intentionally simpler than `ESP32JTAG`.

## 5. Current Reality

Today `meter_native_api` already does the useful work:

- identity
- capabilities
- status
- doctor
- three main actions

But it is still weaker as a model because:

- `instrument_family` is not explicit
- status domains are not normalized
- lifecycle ownership is not carried by the profile itself

## 6. Boundary Decision

The backend/action split should remain:

- `esp32_meter backend` owns action execution
- `meter_native_api` owns instrument identity, status, doctor, and action-level
  entry semantics

This is slightly different from `ESP32JTAG`, where action execution is more
clearly separated out into the backend while the native API remains mostly
metadata/status/doctor.

## 7. Recommendation

Do not start with a backend refactor.

Start by clarifying:

- `instrument_family`
- meter status domains
- lifecycle boundary
- runtime presentation
