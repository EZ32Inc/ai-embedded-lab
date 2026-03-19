# JTAG Native API Transition Plan

Date: 2026-03-19

## Purpose

Define how AEL could introduce `jtag_native_api` gradually without destabilizing
current `esp32_jtag` backend execution.

This is a transition memo only.

## Current State

Today:

- `control_instrument_native_api` provides generic control metadata/status/doctor
- `esp32_jtag` backend provides action execution

That works, but it leaves `ESP32JTAG` under-described at the instrument level.

## Transition Principle

Do not migrate everything at once.

Introduce `jtag_native_api` first as a naming and object-model clarification
layer.

## Recommended Sequence

### Phase 1. Add Interface Layer

Add `jtag_native_api` as a new instrument-level interface surface for:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

Do not move backend action execution yet.

### Phase 2. Route ESP32JTAG Metadata Calls

Change instrument metadata/status/doctor entry points so `ESP32JTAG` uses:

- `jtag_native_api`

while meter continues to use:

- `meter_native_api`

and generic fallback remains available where needed.

### Phase 3. Review Runtime Labels

Update documentation and reporting labels where appropriate so the runtime path
makes a clearer distinction between:

- instrument-level native API surface
- backend action execution surface

### Phase 4. Optional Narrow Action Migration

Only if useful, move a small number of instrument-level actions into
`jtag_native_api`, such as:

- `preflight_probe`
- `capture_signature`

Keep flash/reset/debug execution in `esp32_jtag backend` unless there is a clear
benefit to moving them.

## What Should Stay Where

Recommended long-term split:

### Stay In `jtag_native_api`

- identity
- capabilities
- status
- doctor
- instrument-family specific health semantics

### Stay In `esp32_jtag backend`

- flash
- reset
- debug actions
- gpio measure execution
- transport implementation details

## Documentation Impact

If `jtag_native_api` is introduced later, these docs should be updated together:

- `ESP32JTAG` interface memo
- backend unification status note
- README milestone/status summaries

## Runtime/CLI Impact

Expected low-risk changes:

- `instrument_doctor` can report `ESP32JTAG` through its own named native API
- instrument metadata views can show `instrument_family=esp32jtag`
- backend execution remains stable

## Conclusion

The safe migration path is:

- clarify instrument interface first
- migrate metadata/status/doctor next
- leave action backend execution alone unless there is a specific reason to move
