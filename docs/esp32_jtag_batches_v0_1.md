# ESP32-JTAG Batches v0.1

Date: 2026-03-18
Status: Active Draft

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

- [ ] one end-to-end smoke run passes
- [ ] run goes through AEL, not just a local backend smoke script
- [ ] repeated run count reaches at least 5
- [ ] logs/results are understandable enough for AI consumption
- [ ] failure notes are recorded if repeatability is not yet stable

### Definition Of Done

- Phase 1 backend is not just implemented, it is bench-proven through AEL

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

- [ ] placeholder files exist
- [ ] capability declaration is explicit about support level
- [ ] unsupported behavior is contract-correct
- [ ] future action landing zones are now fixed

### Definition Of Done

- reference backend package shape is complete
- future debug work can land without restructuring the package

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

- [ ] compare ST-Link backend against the reference backend structure
- [ ] identify result-shape drift
- [ ] identify error-code drift
- [ ] identify action-boundary drift
- [ ] apply first narrow alignment pass or record a migration checklist

### Definition Of Done

- ESP32-JTAG is now actually being used as the standard
- ST-Link alignment has started in a controlled way

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

