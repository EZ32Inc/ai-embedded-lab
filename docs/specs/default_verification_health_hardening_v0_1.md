# Default Verification Health Hardening v0.1

## Purpose

Define the bounded health-check intent for `verify-default` after Local
Instrument Interface Phase 2 closeout.

## Intent

This phase is not a runtime rewrite.

It exists to improve confidence that:

- the three default-verification paths remain healthy under repeated use
- repeat-mode results expose useful pass/fail and failure-category evidence
- the expected Local Instrument Interface runtime path remains visible in health
  output

## What This Phase Adds

- bounded repeat/health evidence for `verify-default repeat --limit N`
- explicit pass/fail totals in repeat health output
- observed failure-category counts when failures occur
- surfaced `local_instrument_interface_path` for the default-verification
  workers:
  - `control_instrument_native_api`
  - `meter_native_api`

## What This Phase Does Not Add

- broad runtime migration
- broader generated-example work
- new instrument families
- broad observability redesign outside default verification

## Working Rule

Use this phase to improve confidence and repeatability evidence, not breadth.

If a future batch starts changing unrelated runtime paths or non-default flows,
it is outside this bounded health-hardening phase.
