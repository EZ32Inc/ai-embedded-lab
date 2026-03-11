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

## Deprecation Plan

### Phase 1: Demote in active outputs

Status: largely complete.

Meaning:
- active runtime, summary, explain, inventory, and workflow-archive outputs should present `control_instrument*` as the primary contract
- legacy `probe*` fields should appear only under explicit `compatibility` objects

### Phase 2: Stop expanding compatibility

Status: active now.

Rules:
- new code must not introduce fresh primary `probe*` fields
- new tests should assert canonical `control_instrument*` structures first
- new docs should describe probe wording as legacy compatibility unless the topic is specifically historical policy

### Phase 3: Remove compatibility where consumers are known

This should happen only after:
- the main CLI and docs no longer present `probe*` as a current contract
- core tests treat `probe*` as compatibility-only
- archive and result consumers are identified or migrated

Near-term target:
- keep compatibility explicit and narrow
- shrink it surface by surface instead of attempting a risky repo-wide removal

## Current Remaining Compatibility Surface

Still intentionally present:
- legacy board/probe aliases inside explicit `compatibility` objects
- older raw config names such as `probe_config`
- selected internal helper/wrapper names where immediate removal would create excessive churn

Should no longer be treated as primary:
- live runtime summaries
- workflow archive primary fields
- canonical plan/report contracts

## Current Deprecation Boundary

Keep for now:
- raw compatibility objects in runtime/archive payloads
- legacy config names such as `probe_config`
- internal wrappers whose removal would cause broad adapter churn

Prefer to retire next:
- older user-visible doc/examples that still present `probe` as a current primary term
- remaining machine-readable payload examples that still show `probe_id` without a compatibility note
