# Degraded Instrument Policy Usage

## Purpose

Explain how to read and use degraded-instrument policy information in AEL worker, suite, and repeat-mode results.

## Scope

This applies mainly to default verification and other meter-backed or externally instrumented verification paths.

## Required Result Fields

Prefer reading:
- `failure_class`
- `instrument_condition`
- `failure_scope`
- `degraded_instrument_policy`
- `retry_summary`
- `health_summary`

## Interpretation Guide

Current policy classes:
- `bench_degraded_fail_fast`
- `bench_degraded_retry_once`
- `verify_no_retry`

Read them as operator policy, not as physical root-cause claims.

Examples:
- `instrument_unreachable` + `bench_degraded_fail_fast`
  means the instrument path was not usable enough to justify retry
- `instrument_api_unavailable` + `bench_degraded_retry_once`
  means AEL treated the failure as transient enough for one retry
- `instrument_verify_failed` + `verify_no_retry`
  means the instrument path was usable enough to reach verify, so the failure was preserved rather than retried away

## Diagnosis Workflow

1. Read `instrument_condition`.
2. Read `failure_scope`.
3. Read `policy_class`.
4. Read `retry_summary`.
5. Only then decide whether you are looking at bench degradation, verify-stage mismatch, or something unrelated to instrument state.

## Current Known Conclusions

- classification/reporting policy is already real and should be treated as stable enough for operational use
- deeper recovery policy is still intentionally bounded

## Related Files

- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
- [degraded_instrument_handling.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/degraded_instrument_handling.md)
- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
