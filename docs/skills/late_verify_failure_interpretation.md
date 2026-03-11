# Late Verify Failure Interpretation

## Purpose

Explain how to interpret failures that occur after build/flash and only fail during `verify`.

## Scope

This applies to AEL runs where:
- the worker did not fail in early bench readiness checks
- build and flash already succeeded
- the failure surfaced in `verify`

## Required Observations

Prefer reading:
- `verify_substage`
- `failure_class`
- `instrument_condition`
- `failure_scope`
- `error_summary`
- `verify_result.json`

## Interpretation Guide

Key meanings:
- `failure_scope=verify`
  means the path was usable enough to reach verification
- `instrument_condition=instrument_verify_failed`
  means the instrument path was present, but verification through it failed

Common useful separation:
- `uart.verify`
  firmware/runtime readiness issue
- `instrument.signature`
  digital/analog signature or backend-side verification issue

Do not interpret a late verify failure as the same class of problem as:
- unreachable instrument
- transport/API readiness failure

## Diagnosis Workflow

1. Confirm that build and flash succeeded.
2. Read `verify_substage`.
3. Read `failure_class`.
4. Open `verify_result.json` if the suite-level payload is still too sparse.
5. Decide whether the evidence points more to DUT behavior, instrument behavior, or mixed verify-path instability.

## Current Known Conclusions

- late verify failures should preserve structured verify details in suite-level results when possible
- current AEL now has a fallback path that can promote details from `verify_result.json` when the direct suite-level payload is too thin
- if they do not, `verify_result.json` remains the authoritative fallback

## Related Files

- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
