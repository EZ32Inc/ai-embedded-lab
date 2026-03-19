# ESP32-JTAG Batches v0.1

Date: 2026-03-18
Status: Batch 6 Complete

## Purpose

This document turns the ESP32-JTAG implementation plan into six concrete delivery batches.

Use this as the execution tracker for the reference implementation work.

Related docs:

- [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md)
- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)
- [esp32_jtag_backend_skeleton_v0_1.md](./esp32_jtag_backend_skeleton_v0_1.md)
- [esp32_jtag_implementation_plan_v0_1.md](./esp32_jtag_implementation_plan_v0_1.md)

## Batch 1: Skeleton And First Action

### Scope

- add a new driver path, preferably `esp32_jtag`
- create the backend package skeleton
- implement only `reset`
- make unsupported actions return structured failure

### Files

- `ael/instruments/dispatcher.py`
- `ael/instruments/backends/esp32_jtag/__init__.py`
- `ael/instruments/backends/esp32_jtag/backend.py`
- `ael/instruments/backends/esp32_jtag/transport.py`
- `ael/instruments/backends/esp32_jtag/errors.py`
- `ael/instruments/backends/esp32_jtag/capability.py`
- `ael/instruments/backends/esp32_jtag/actions/__init__.py`
- `ael/instruments/backends/esp32_jtag/actions/reset.py`

### Checklist

- [ ] new backend package exists
- [ ] dispatcher recognizes `esp32_jtag`
- [ ] backend imports cleanly
- [ ] `reset` action works through dispatcher
- [ ] unsupported actions return structured failure

### Definition Of Done

- dispatcher can route to the new backend
- package structure matches the skeleton doc
- one implemented action proves the pattern is real

### Do Not Do In This Batch

- do not refactor `esp_remote_jtag`
- do not add `flash`
- do not add `gpio_measure`
- do not align ST-Link yet

## Batch 2: Complete Phase 1 Actions

### Scope

- implement `flash`
- implement `gpio_measure`
- keep the same backend separation and result normalization pattern

### Files

- `ael/instruments/backends/esp32_jtag/actions/flash.py`
- `ael/instruments/backends/esp32_jtag/actions/gpio_measure.py`
- optional refinements in `transport.py` and `backend.py`

### Checklist

- [ ] `flash` validates request fields
- [ ] `flash` validates firmware path
- [ ] `gpio_measure` validates channel input
- [ ] all three Phase 1 actions use the same error normalization path
- [ ] no action logic is collapsed back into `backend.py`

### Definition Of Done

- `flash`, `reset`, and `gpio_measure` all exist and are callable
- Phase 1 action set matches the reference docs

### Do Not Do In This Batch

- do not add debug actions yet
- do not widen into ST-Link migration

## Batch 3: Structural Tests

### Scope

- add unit and dispatcher-level tests for the new backend
- prove success and failure contracts

### Suggested Files

- `tests/test_esp32_jtag_backend.py`
- `tests/test_esp32_jtag_transport.py`
- `tests/test_esp32_jtag_dispatcher.py`

### Checklist

- [ ] unsupported action test exists
- [ ] invalid request test exists
- [ ] invalid firmware path test exists
- [ ] invalid `reset_kind` test exists
- [ ] transport unreachable test exists
- [ ] timeout test exists
- [ ] measurement failure mapping test exists
- [ ] dispatcher integration test exists

### Definition Of Done

- structural behavior is tested without requiring live hardware
- failure shape is as intentional as success shape

### Do Not Do In This Batch

- do not depend on live bench for core correctness

## Batch 4: Live AEL Validation

### Scope

- connect the backend to one real AEL flow
- run the reference smoke path through AEL
- repeat it

### Validation Flow

- `flash -> reset -> gpio_measure`

### Checklist

- [x] one end-to-end smoke run passes
- [x] run goes through AEL, not just a local backend smoke script
- [x] repeated run count reaches at least 5
- [x] logs/results are understandable enough for AI consumption
- [x] failure notes are recorded if repeatability is not yet stable

### Definition Of Done

- Phase 1 backend is not just implemented, it is bench-proven through AEL

### Result

Completed on `2026-03-18`.

Validated path:

- board: `stm32f411ceu6`
- test: `tests/plans/stm32f411_gpio_signature.json`
- control instrument: `esp32jtag_stm32f411 @ 192.168.2.103:4242`
- flow: `flash -> reset/run -> gpio verification`

Live repeat runs:

- `2026-03-18_20-37-54_stm32f411ceu6_stm32f411_gpio_signature`
- `2026-03-18_20-38-11_stm32f411ceu6_stm32f411_gpio_signature`
- `2026-03-18_20-38-46_stm32f411ceu6_stm32f411_gpio_signature`
- `2026-03-18_20-39-15_stm32f411ceu6_stm32f411_gpio_signature`
- `2026-03-18_20-39-41_stm32f411ceu6_stm32f411_gpio_signature`
- `2026-03-18_20-40-08_stm32f411ceu6_stm32f411_gpio_signature`

Observed outcome:

- `6/6` live runs passed during the Batch 4 closeout session
- preflight reached the probe and LA API successfully on each run
- flash succeeded on attempt 1 on each run
- verification passed on each run with stable GPIO capture

Notes:

- one non-escalated local attempt failed before validation because sandbox networking blocked access to `192.168.2.103`; this was an execution-environment issue, not a bench failure
- the `5`-run initial stability threshold from the validation plan is now satisfied

### Do Not Do In This Batch

- do not start another backend until this one is stable enough

## Batch 5: Phase 2 Placeholders

### Scope

- add placeholder files for `debug_halt`
- add placeholder files for `debug_read_memory`
- make unsupported or not-yet-implemented behavior explicit and structured

### Files

- `ael/instruments/backends/esp32_jtag/actions/debug_halt.py`
- `ael/instruments/backends/esp32_jtag/actions/debug_read_memory.py`

### Checklist

- [x] placeholder files exist
- [x] capability declaration is explicit about support level
- [x] unsupported behavior is contract-correct
- [x] future action landing zones are now fixed

### Definition Of Done

- reference backend package shape is complete
- future debug work can land without restructuring the package

### Result

Completed on `2026-03-18`.

Implemented:

- `ael/instruments/backends/esp32_jtag/actions/debug_halt.py`
- `ael/instruments/backends/esp32_jtag/actions/debug_read_memory.py`

Behavior:

- direct backend calls now return explicit structured `not_implemented` failures for both Phase 2 actions
- capability declaration still reports `supports_debug_halt: false` and `supports_debug_read_memory: false`
- `supports_action(...)` remains limited to the implemented Phase 1 action set

Validation:

- placeholder behavior covered in `tests/test_esp32_jtag_backend.py`

### Do Not Do In This Batch

- do not fake full debug semantics if hardware behavior is not ready

## Batch 6: First Alignment Migration

### Scope

- begin alignment of legacy backends using ESP32-JTAG as the template
- start with ST-Link
- keep migration narrow and explicit

### Primary Target

- `ael/instruments/backends/stlink.py`

### Checklist

- [x] compare ST-Link backend against the reference backend structure
- [x] identify result-shape drift
- [x] identify error-code drift
- [x] identify action-boundary drift
- [x] apply first narrow alignment pass or record a migration checklist

### Definition Of Done

- ESP32-JTAG is now actually being used as the standard
- ST-Link alignment has started in a controlled way

### Result

Completed on `2026-03-18`.

Applied changes:

- added typed ST-Link backend exceptions and error-code normalization
- split ST-Link into a package:
  - `ael/instruments/backends/stlink_backend/backend.py`
  - `ael/instruments/backends/stlink_backend/transport.py`
  - `ael/instruments/backends/stlink_backend/capability.py`
  - `ael/instruments/backends/stlink_backend/errors.py`
  - `ael/instruments/backends/stlink_backend/actions/*.py`
- kept `ael/instruments/backends/stlink.py` as a compatibility shim for dispatcher and test imports
- added a structured backend wrapper class with:
  - explicit handler map
  - `capabilities()`
  - `supports_action(...)`
  - structured `execute(...)` results
- kept a result bridge so `invoke(...)` still returns the existing IAM legacy shape for dispatcher compatibility

Drift addressed in this pass:

- result-shape drift:
  - direct backend execution now has a structured `status/action/error` shape similar to `esp32_jtag`
- action-boundary drift:
  - ST-Link now uses an explicit handler map and per-action modules instead of a single monolithic file
- capability drift:
  - ST-Link now has an explicit capability declaration
- error normalization drift:
  - ST-Link now uses typed exceptions and mapped backend error codes on the direct path

Still intentionally deferred:

- global IAM result-helper migration
- any forced shared transport abstraction between ESP32-JTAG and ST-Link beyond the existing GDB-remote overlap

Validation:

- added `tests/test_stlink_backend.py`
- verified with:
  - `PYTHONPATH=. pytest -q tests/test_esp32_jtag_backend.py tests/test_esp32_jtag_transport.py tests/test_esp32_jtag_dispatcher.py tests/test_stlink_backend.py`
- live ST-Link validation passed:
  - `2026-03-18_21-06-44_stm32f407_discovery_stm32f407_mailbox`
  - board: `stm32f407_discovery`
  - test: `tests/plans/stm32f407_mailbox.json`
  - result: `PASS`

### Do Not Do In This Batch

- do not rewrite ST-Link and USB-UART together
- do not add broad new instrument features in the same batch

## Batch Checkpoints

### Checkpoint A

After Batch 2:

- Phase 1 action coverage review

### Checkpoint B

After Batch 3:

- structural contract review

### Checkpoint C

After Batch 4:

- live validation review

### Checkpoint D

After Batch 6:

- migration strategy review

## Summary

The intended progression is:

1. create the reference backend shape
2. complete the Phase 1 action set
3. prove the contract in tests
4. prove the backend on live AEL runs
5. complete the package shape for future debug actions
6. use the result to align the rest of the instrument layer
