# Controller Unification Status Closeout (2026-03-20)

## Summary

The repo has moved beyond a unified instrument interface skeleton.

The active system now exposes a first working controller/instrument model across:

- interface providers
- action envelopes
- doctor/status/capability semantics
- runtime reporting
- workflow archive events
- CLI entry points
- default verification resolution
- family-native backend delegation

This is not yet the end state. The remaining work is now mostly legacy-seam cleanup, not architecture definition.

## Completed Layers

### 1. Interface Spine

The active interface spine is provider-based and registry-routed for the main families:

- `stlink`
- `esp32jtag`
- `esp32_meter`
- `usb_uart_bridge`

The active callers now route through `ael/instruments/interfaces/`.

### 2. Semantic Model V1

A first working semantic layer is in place:

- capability taxonomy documented in `docs/instrument_model_v1.md`
- shared action/result envelope in `ael/instruments/interfaces/model.py`
- unified `doctor/status/capabilities` top-level semantics
- real migrated actions across the four main families

### 3. Public Vocabulary Shift

Public higher-layer vocabulary has been shifted toward:

- `instrument_interface`
- `instrument_family`
- `controller`

Compatibility aliases are still present where needed.

### 4. Runtime Surfaces Converted

The following active runtime/user-visible surfaces now emit or consume controller/instrument-neutral vocabulary:

- instrument view
- instrument doctor
- stage explain
- pipeline summaries
- staged execution summaries
- default verification reporting
- workflow archive event payloads
- inventory describe output
- `la_check` output
- CLI `--controller` alias

### 5. Backend Boundary Tightening

A neutral backend facade now exists:

- `ael/instruments/controller_backend.py`

`jtag_native_api.py` and `stlink_native_api.py` no longer call `control_instrument_native_api.py` directly for their shared control-path actions.

## Key Commit Chain

The main consolidation sequence is:

- `80e5e9b` `Unify instrument semantics and reporting`
- `b542666` `Restart stale local ST-Link gdb server`
- `0981c2e` `Rename public instrument interface fields`
- `b534d01` `Add neutral controller aliases`
- `8407702` `Add controller aliases to inventory and resolver`
- `a59db77` `Expose controller aliases in la_check`
- `1e3f04e` `Promote controller aliases in staged summaries`
- `193483c` `Archive controller aliases in workflow events`
- `3faa3f3` `Add controller alias to CLI`
- `8d3ad68` `Use controller aliases in default verification`
- `b8a833d` `Add neutral controller backend facade`

## What Is Still Not Fully Unified

### 1. Legacy Backend Module Naming

The repo still contains:

- `control_instrument_native_api.py`
- `jtag_native_api.py`
- `stlink_native_api.py`
- `meter_native_api.py`

These are now closer to backend details, but the naming itself is still legacy-oriented.

### 2. Legacy Compatibility Payloads

Many active payloads intentionally still carry compatibility fields such as:

- `control_instrument`
- `control_instrument_config`
- `control_instrument_instance`
- `probe` compatibility blocks

This is acceptable for the current migration stage, but it is not the final model.

### 3. Historical Artifacts and Snapshots

Reference snapshots, archived logs, and older docs still contain historical vocabulary.

These are not active architecture blockers, but they do create noise when judging whether the repo is fully converged.

## Current Engineering Judgment

The project has crossed from:

- interface unification

into:

- active semantic unification of the main execution surfaces

The next work should not be another large architecture rewrite. It should be a controlled retirement of the remaining legacy seams.

## Recommended Next Slice

The next highest-value cleanup slice is:

1. reduce direct first-class status of `control_instrument_native_api.py`
2. formalize backend ownership naming around `controller_backend`
3. shrink compatibility payload duplication where live callers no longer need it
4. update older user-facing docs and reference snapshots only after active code paths are stable
