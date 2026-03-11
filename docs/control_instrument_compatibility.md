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
- remaining top-level CLI/help examples that still mention `--probe` outside an explicit legacy-compatibility context

Current practical examples of "retire next":
- older phase and trace docs that still say `board/probe/test`
- active guidance docs that still say "probe or instrument" where the intended current meaning is "control instrument or instrument"

Deferred while degraded-instrument policy settles:
- low-level helper and adapter parameter names that still use `probe_cfg`
- compatibility wrappers whose removal would mix naming churn with runtime policy work

## Practical Review Table

### Keep for now

- explicit `compatibility.probe*` objects in runtime/archive payloads
- legacy raw config keys such as `probe_config`
- low-level internal helper names whose cleanup would create broad adapter churn
- internal step/adaptor parameters such as `probe_cfg` and `probe_path` where the current naming is still mostly an implementation seam, not a user-facing contract

### Retire next

- active docs/examples that still say `board/probe/test`
- active docs that still say `probe or instrument` where the current intended distinction is `control instrument or instrument`
- visible CLI/help/example text that mentions `--probe` without immediately calling it legacy
- compatibility-heavy payload examples that still show top-level `probe*` forms without an explicit compatibility note

### Defer

- broad internal helper renames
- compatibility removal from archived payload readers
- adapter parameter renames that do not affect current user-facing clarity

## Current Practical Conclusion

The remaining compatibility surface is now mostly:

- internal implementation seams
- explicit compatibility payload objects
- older examples/specs

This means Phase 2 should not chase broad internal renames unless they unlock real clarity or reduce real maintenance cost.
The higher-value remaining work is selective user-facing cleanup and careful policy/contract review.

## Current Working Boundary

Active user-facing/runtime-facing surfaces should now read as:

- control-instrument-first
- DUT and board-profile separated
- bench resources compared through `selected_bench_resources`

This means the main remaining cleanup target is no longer runtime summaries.
It is active documentation/examples plus older compatibility-oriented wording that users can still encounter.

Legacy `probe*` remains acceptable only when:

- reading historical archived payloads
- supporting older callers
- discussing legacy fallback policy explicitly
