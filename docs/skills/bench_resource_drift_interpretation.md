# Bench Resource Drift Interpretation

## Purpose

Explain how to interpret `bench_resource_drift_from_lkg` and related bench-resource fields in AEL outputs.

## Scope

This skill applies to:
- `verify-default` validation summaries
- last-known-good comparison output
- structured runtime/archive payloads with `selected_bench_resources`

## Background

AEL now emits a canonical bench-resource object:
- `selected_bench_resources`

The preferred compact comparison fields are:
- `contract_version`
- `selection_digest`

Supporting detail remains available in:
- `resource_keys`
- `resource_summary`
- `connection_digest`

## Required Observations

Collect:
- current `selected_bench_resources`
- last-known-good `selected_bench_resources`
- `bench_resource_drift_from_lkg`
- worker `resource_keys` and `resource_summary` if concurrency questions matter

## Interpretation Guide

Treat drift as a setup comparison, not automatic proof of failure cause.

Typical meanings:
- `selection_digest` drift:
  the selected bench endpoint, serial path, SSID, or control-instrument instance changed
- `resource_keys` drift:
  lock-relevant runtime ownership changed
- `connection_digest` drift:
  the declared bench wiring/setup meaning changed

If only bench-resource drift changed while verification still passed:
- treat it as setup drift, not a bug by itself

If drift changed and a failure appeared:
- consider the drift a likely bench-context change that should be evaluated first

## Diagnosis Workflow

1. Read the compact drift line from the summary.
2. Compare current and LKG `selection_digest`.
3. Check whether `resource_keys` changed in a lock-relevant way.
4. Check whether `connection_digest` changed in a meaningfully different wiring/setup way.
5. Only after that, decide whether the failure points to DUT behavior, bench drift, or unrelated instability.

## Current Known Conclusions

- `selection_digest` is the preferred first comparison surface
- `resource_keys` explain lock-relevant ownership
- `connection_digest` explains declared setup meaning

## Unresolved Questions

- whether future benches need more explicit resource classes in the compact digest

## Related Files

- [bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)
- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [inventory.py](/nvme1t/work/codex/ai-embedded-lab/ael/inventory.py)
