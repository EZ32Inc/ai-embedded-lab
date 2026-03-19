# JTAG Native API Implementation Review

Date: 2026-03-19

## Purpose

Review the minimum implementation cut for introducing `jtag_native_api`
without destabilizing the current `esp32_jtag` backend execution path.

This is an implementation review memo only.

It does not apply code changes.

## Scope

This review covers only the first implementation slice:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

It explicitly excludes:

- backend action refactors
- dispatcher changes for runtime action execution
- transport rewrites

## Current Relevant Files

### Current Generic Native Layer

- [ael/instruments/control_instrument_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/control_instrument_native_api.py)

Current role:

- generic control-instrument metadata
- generic status/doctor
- generic preflight/program/capture helpers

### Current JTAG Action Backend

- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)

Current role:

- `flash`
- `reset`
- `gpio_measure`
- debug placeholders

### Current Native Dispatch

- [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)

Current role:

- meter native routing
- generic control native routing

### Current Doctor Entry

- [ael/instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)

Current role:

- doctor for instrument manifests
- doctor for control instrument instances

### Current Instrument View

- [ael/instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)

Current role:

- resolved instrument manifest view
- resolved control instrument instance view

## Recommended New File

The minimum new file should be:

- `ael/instruments/jtag_native_api.py`

Reason:

- keep JTAG instrument identity separate from the generic control abstraction
- avoid mixing family-specific metadata back into
  `control_instrument_native_api.py`

## Recommended Responsibilities

### `jtag_native_api.py`

Should own:

- `native_interface_profile()`
- `identify(probe_cfg)`
- `get_capabilities(probe_cfg)`
- `get_status(probe_cfg)`
- `doctor(probe_cfg)`

Should not own, in the first implementation:

- `flash`
- `reset`
- `gpio_measure`
- debug execution

Those should remain where they already live:

- `esp32_jtag backend`
- generic control helpers if still needed

## Recommended Dispatch Change

The narrowest safe dispatch change would be in:

- [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)

Recommended change:

- keep meter manifest routing as-is
- add a JTAG-family routing branch for the new native metadata/status/doctor calls
- keep generic control action helpers in place

Important distinction:

- manifest-based instrument routing should eventually use `jtag_native_api`
- probe/action helper functions like `preflight_probe(...)` and
  `program_firmware(...)` do not need to move in the first batch

## Recommended Doctor Change

The minimum doctor change is in:

- [ael/instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)

Recommended change:

- today, only `esp32s3_dev_c_meter` has an active manifest-native doctor path
- after `jtag_native_api` exists, `ESP32JTAG` instrument manifests or resolved
  JTAG instrument views should use that path too

This is the cleanest place to make the new interface visible first.

## Recommended View Change

The minimum view change is in:

- [ael/instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)

Recommended change:

- once `jtag_native_api` exists, expose:
  - `instrument_family=esp32jtag`
  - native interface summary for JTAG
  - multi-endpoint semantics where available

This is lower priority than doctor/native dispatch, but it is a useful early
consumer of the new interface definition.

## What Should Not Change In The First Batch

These should remain untouched in the first implementation:

- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)
- [ael/instruments/backends/esp32_jtag/transport.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/transport.py)
- dispatcher action routing for `esp32_jtag`
- live runtime execution path

Reason:

- the goal of the first batch is interface clarification, not backend behavior
  migration

## Minimum Testing Surface For The First Batch

When implementation starts, the first batch should add only narrow tests:

- `tests/test_jtag_native_api.py`
  - identify payload
  - get_capabilities payload
  - get_status payload
  - doctor payload
- update `tests/test_native_api_dispatch.py`
  - ensure JTAG family routing works
- update doctor/view tests only if output shape changes there

## Minimum Implementation Sequence

1. add `ael/instruments/jtag_native_api.py`
2. add unit tests for the new native layer
3. teach `native_api_dispatch.py` to route JTAG metadata/status/doctor calls
4. teach `instrument_doctor.py` to use the new JTAG-native path
5. optionally update `instrument_view.py` if needed for visibility

## Final Recommendation

The smallest correct implementation cut is:

- add `jtag_native_api.py`
- route metadata/status/doctor through it
- do not touch `esp32_jtag backend` execution

That is the safest next implementation batch.
