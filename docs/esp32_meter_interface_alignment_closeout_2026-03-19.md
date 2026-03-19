# ESP32 Meter Interface Alignment Closeout

Date: 2026-03-19

## Scope

This closeout records the bounded batch that aligned `ESP32 meter` more closely
with the runtime-facing instrument-interface shape already used for
`ESP32JTAG`.

Completed scope:

- clarify meter native instrument identity
- add explicit meter status domains
- add lifecycle boundary metadata to the native profile
- align instrument view / doctor presentation with `instrument_family = esp32_meter`
- verify the change with targeted tests
- refresh one real meter-backed live validation path

Out of scope:

- changing backend action ownership
- moving provision / Wi-Fi onboarding into the backend
- introducing new meter actions

## What Changed

Implementation:

- [ael/instruments/meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)
- [ael/instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)
- [ael/instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)

Key interface outcomes:

- `instrument_family = esp32_meter`
- `device_type = measurement_and_stimulus_instrument`
- `instrument_role = external_instrument`
- status domains:
  - `network`
  - `meter_service`
  - `measurement_surface`
  - `stimulation_surface`
- lifecycle boundary is now explicit in the native interface profile

## Verification

Targeted tests:

- `tests/test_meter_native_api.py`
- `tests/test_instrument_view.py`
- `tests/test_instrument_doctor.py`
- `tests/test_native_api_dispatch.py`

Observed result:

- `18 passed`

## Live Validation Refresh

Live path:

- test: `esp32c6_gpio_signature_with_meter`
- board: `esp32c6_devkit`
- instrument: `esp32s3_dev_c_meter @ 192.168.4.1:9000`

Result:

- refreshed in this batch to confirm the runtime-facing interface alignment did
  not break real meter-backed execution

## Reusable Conclusions

- meter interface clarification can be done without reopening backend
  migration work
- explicit instrument identity and status domains improve runtime legibility
  without changing action ownership
- `instrument_view` and `instrument_doctor` can be aligned by injecting the
  runtime native profile for the active manifest family instead of waiting for a
  broader registry refactor
