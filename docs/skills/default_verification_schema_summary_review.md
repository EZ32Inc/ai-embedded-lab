# Default Verification Schema Summary Review

Use this when `default_verification` has started emitting suite-level `schema_advisory_summary` and you need to decide whether the run is structurally healthy before digging into lower-level artifacts.

## Purpose

- Read the suite-level schema summary before inspecting individual failures.
- Separate schema/support mismatches from bench/runtime failures.
- Keep review fast when a run mixes legacy and structured plans.

## Where to look

- final JSON payload from `python3 -m ael verify-default run ...`
- stdout summary lines beginning with:
  - `[SUMMARY] schema`
  - `[SUMMARY] schema_test_kinds`
  - `[SUMMARY] schema_instrument_support`
  - `[SUMMARY] schema_warnings`

## Key fields

- `schema_advisory_summary.structured_step_count`
- `schema_advisory_summary.legacy_step_count`
- `schema_advisory_summary.test_kind_counts`
- `schema_advisory_summary.supported_instrument_status_counts`
- `schema_advisory_summary.warning_messages`
- `schema_advisory_summary.instrument_specific_steps`

## Fast interpretation

- `structured_step_count > 0` and no warnings:
  - structured advisory metadata is flowing through the suite normally
- `supported_instrument_status_counts.declared_supported` dominates:
  - instrument selection is aligned with plan declarations
- any `declared_unsupported` count:
  - treat as operator-actionable warning first, not automatic runner failure cause
- non-empty `warning_messages`:
  - surface them early in the review summary
- mix of `structured` and `legacy`:
  - expect partial advisory coverage; do not over-interpret missing schema data on legacy plans

## Recommended review order

1. Read `schema_advisory_summary`.
2. Check whether warnings are schema/support mismatches or actual execution failures.
3. Only then inspect per-step `result`, `verify_result.json`, `flash.log`, or `evidence.json`.

## Representative validation pattern

- For new structured meter banner plans, validate one single-run representative path first.
- Example good path:
  - board: `esp32c6_devkit`
  - test: `tests/plans/esp32c6_spi_banner.json`

## Reusable takeaway

- The suite-level schema summary is the quickest way to tell whether a run failed because of execution behavior or because plan/instrument declarations are out of alignment.
