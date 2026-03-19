# ESP32 Instrument Backend Unification Status

Date: 2026-03-19

## Purpose

Record the current unification status for the two ESP32-based instrument lines:

- `ESP32JTAG`
- `ESP32-S3 meter`

The question is not whether they are usable today, but whether they are already
packaged behind the same kind of unified instrument backend boundary used by
newer IAM-style instrument backends such as `stlink` and `esp32_jtag`.

## Short Answer

- `ESP32JTAG`: yes, largely complete
- `ESP32-S3 meter`: not yet complete

## ESP32JTAG Status

`ESP32JTAG` now has a reference-style IAM backend package:

- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)
- [ael/instruments/backends/esp32_jtag/transport.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/transport.py)
- [ael/instruments/backends/esp32_jtag/capability.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/capability.py)
- action modules under
  [ael/instruments/backends/esp32_jtag/actions](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/actions)

Dispatcher integration is explicit:

- [ael/instruments/dispatcher.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/dispatcher.py)
  maps `esp32_jtag` to the backend package

Current result:

- flash/reset/gpio_measure are integrated through the unified instrument backend path
- debug placeholder actions exist
- this line is already in the same packaging family as `stlink_backend`

Conclusion:

- `ESP32JTAG` can be treated as already unified at the backend-package level

## ESP32-S3 Meter Status

The meter line is usable, but not yet packaged the same way.

Current active pieces are:

- low-level TCP adapter:
  [ael/adapters/esp32s3_dev_c_meter_tcp.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/esp32s3_dev_c_meter_tcp.py)
- native API wrapper:
  [ael/instruments/meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)
- native dispatch special-casing:
  [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)
- adapter-registry special backend:
  [ael/adapter_registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapter_registry.py)

What is missing compared with `ESP32JTAG` and `ST-Link`:

- no dedicated IAM backend package under
  `ael/instruments/backends/<meter_backend>/`
- no dispatcher driver entry like:
  `driver -> backend package`
- no explicit backend wrapper class with handler map
- no action modules split by capability
- no alignment to the newer backend package shape used by:
  - `esp32_jtag`
  - `stlink_backend`

Conclusion:

- the meter path currently has a bounded native API and runtime integration
- but it is not yet fully wrapped as a unified IAM backend package

## Current Boundary

The current state is mixed:

- `ESP32JTAG` is in the newer unified backend family
- `ST-Link` is in the newer unified backend family
- `USB-UART bridge` has a backend, but still in single-file legacy shape
- `ESP32-S3 meter` is still primarily adapter/native-dispatch driven

So the answer to "is instrument packaging unified already?" is:

- for `ESP32JTAG`: mostly yes
- for `ESP32-S3 meter`: no, not to the same standard yet

## Implementation Gap For Meter

To reach parity with `ESP32JTAG` / `ST-Link`, meter work should add:

1. backend package
- `ael/instruments/backends/esp32_meter/`

2. explicit wrapper
- `backend.py`
- `capability.py`
- `transport.py`
- `errors.py`

3. action split
- likely:
  - `measure_digital.py`
  - `measure_voltage.py`
  - `stim_digital.py`
  - optional `selftest.py`
  - optional `identify.py` / `status.py` if kept in backend scope

4. dispatcher registration
- add a driver mapping for the meter backend

5. migration boundary decision
- decide what stays in:
  - native API / provision / doctor path
- and what moves into:
  - unified IAM backend path

## Recommendation

Do not redesign meter broadly first.

The best next step is a narrow migration:

- package only the meter action path used by current runtime:
  - digital measure
  - voltage measure
  - digital stimulus
- keep provision / doctor / reachability logic where it is for now

That gives packaging parity without reopening the whole meter architecture.
