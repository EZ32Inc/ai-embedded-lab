# DUT Target Generation Policy v0.1

This document defines the general AEL policy for generating new DUT firmware
targets.

## Purpose

AEL target generation should produce reviewable, repeatable targets with clear
status and provenance. The goal is not just to get a board to compile once. The
goal is to make the source basis, assumptions, and validation state explicit.

## Generation priority

Targets should be created in this order of preference:

1. `verified_local_first`
   - Reuse a locally validated AEL target as the behavioral and structural
     baseline when a close family/device match already exists.
   - This is the preferred starting point for process hardening because it keeps
     behavior anchored to known-good local results.

2. `official_source_second`
   - When official vendor device-support sources are available and materially
     improve correctness, build the new target around them.
   - This is required for formal official-source pilots and should be preferred
     once the local baseline is understood.

3. `provisional_fallback`
   - If no verified local baseline or clean official source path is available,
     a provisional target may be created to support planning and early
     discussion.
   - Provisional targets must be labeled as provisional and must not be
     presented as hardware-validated.

## Required status model

Every generated target should have an explicit status with at least:

- generation class
- validation status
- whether it is recommended as a baseline
- key caveats

These values should be maintained in the STM32 generation catalog for STM32
targets and in equivalent catalogs for other MCU families as they are added.

## Provenance rules

Official-source-based targets must record provenance in a target-local
`provenance.md`.

At minimum, provenance must include:

- upstream source repo
- upstream revision or tag
- copied source paths
- which files are vendor-copied
- which files are AEL-generated
- any local modifications or AEL-specific glue decisions

Provisional and verified-local targets may use lighter provenance notes, but
their source basis still needs to be obvious from the catalog and case-study
docs.

## Validation rules

Validation status must be explicit and conservative.

Allowed examples:

- `hardware_verified_repeated`
- `hardware_verified_single`
- `build_and_plan_verified`
- `plan_verified_only`

Do not claim runtime verification when only plan-stage or build-stage checks
have been completed.

## Required separation of concerns

Generated targets must keep these concerns distinct:

- device facts
  - memory map
  - startup/runtime support
  - vendor headers/system files
- AEL-owned behavior
  - GPIO signature logic
  - UART ready behavior
  - test-specific glue
- board assumptions
  - LED pin
  - bench wiring
  - probe selection

## Catalog requirement

STM32 targets must appear in one shared STM32 generation catalog. The catalog is
the source of truth for:

- target generation class
- validation status
- baseline recommendation
- pilot-candidate assessment

Case-study notes, such as per-target skill files, are examples and should not be
the primary source of policy.
