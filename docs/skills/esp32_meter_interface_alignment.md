# Skill: ESP32 Meter Interface Alignment

## When To Use

Use this when the `ESP32 meter` backend/action path already works, but the
instrument-level runtime model is weaker or less explicit than the
`ESP32JTAG` path.

## Goal

Improve meter identity / status / doctor / runtime presentation without moving
backend ownership.

## Steps

1. Keep backend ownership fixed.
- leave action execution in `esp32_meter backend`
- do not reopen transport migration

2. Clarify identity.
- add `instrument_family = esp32_meter`
- add a more explicit `device_type`
- add `instrument_role`

3. Normalize status domains.
- use stable meter-specific domains such as:
  - `network`
  - `meter_service`
  - `measurement_surface`
  - `stimulation_surface`

4. Make lifecycle boundary explicit.
- add `lifecycle_scope` to the native profile
- keep provision / onboarding out of scope unless a separate batch is justified

5. Align runtime presentation.
- make `instrument_view` show the meter family explicitly
- make `instrument_doctor` render the same family consistently

6. Refresh one real meter-backed path.
- do not stop at tests
- rerun one real bench path to prove the runtime-facing changes did not break
  actual use

## Important Boundary

This is an interface-clarification skill, not a backend-refactor skill.

Good outcome:

- clearer runtime identity
- clearer doctor/status output
- unchanged backend ownership
