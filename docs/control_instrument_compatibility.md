# Control Instrument Compatibility

## Purpose

This note explains which legacy `probe*` structures still remain in AEL and why they still exist.

The preferred model is now:
- `control_instrument`
- `control_instrument_instance`
- `control_instrument_selection`

Legacy `probe` terminology remains only for compatibility with older tooling, older tests, and older archived results.

## Current Preferred Structures

Primary current structures:
- `stage_explain.selected.control_instrument_selection`
- pipeline summary/current-setup/LKG `control_instrument`
- inventory `selected_instrument` with `kind: control_instrument`
- runtime and inventory boundary objects:
  - `selected_dut`
  - `selected_board_profile`
  - `selected_bench_resources`
- instrument doctor and instrument view canonical kinds:
  - `control_instrument`
  - `control_instrument_instance`
- LA check output `control_instrument`

New code should prefer:
- `selected_instrument`
- `control_instrument`
- `control_instrument_selection`

New code should not introduce fresh primary dependencies on:
- `probe_or_instrument`
- `probe_instance`
- `probe_endpoint`
- `probe_communication`

## Remaining Compatibility Fields

Legacy compatibility fields still present in some outputs:
- `probe`
- `probe_instance`
- `probe_type`
- `probe_endpoint`
- `probe_communication`
- `probe_capability_surfaces`
- `probe_or_instrument`

Why they still remain:
- older tests and callers still reference them
- older archived result payloads use them
- removing them immediately would create unnecessary churn while the model migration is still settling
- in active runtime/report outputs, these legacy fields should live under explicit `compatibility` objects rather than as co-equal primary fields

## Intended Interpretation

When both forms are present:
- treat `control_instrument*` as canonical
- treat `probe*` as compatibility aliases

This means:
- new code should prefer the control-instrument structures
- new docs should present control-instrument terminology first
- compatibility logic should remain explicit rather than accidental

## Removal Boundary

Legacy `probe*` fields should only be considered for removal after:
- the main CLI and docs no longer present them as primary
- core tests stop depending on them as primary fields
- archived output consumers are known or migrated

Until then, the repo should aim for:
- canonical control-instrument structures first
- legacy probe fields clearly secondary
