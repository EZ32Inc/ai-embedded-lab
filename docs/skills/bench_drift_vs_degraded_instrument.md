# Bench Drift vs Degraded Instrument

## Purpose

Explain how to separate bench-resource drift from degraded-instrument failure when reading AEL outputs.

## Scope

Use this when:
- a run reports `bench_resource_drift_from_lkg`
- a worker fails with `instrument_condition`
- an operator wants to know whether the problem is "different hardware binding" or "same binding, unhealthy hardware"

## Core Separation

These are different questions:

- `bench_resource_drift_from_lkg`
  asks whether the currently selected bench resources differ from last known good
- `instrument_condition`
  asks whether the bound instrument behaved in a degraded or failing way during this run

Drift does not imply failure.
Failure does not imply drift.

## Read This First

1. `selected_bench_resources.selection_digest`
2. `bench_resource_drift_from_lkg`
3. `failure_class`
4. `instrument_condition`
5. `verify_substage`

## Interpretation Guide

Typical cases:

- Same digest, degraded instrument:
  - bench binding stayed the same
  - current instrument behavior degraded
  - likely unstable instrument, network path, or bench component

- Different digest, no degraded instrument:
  - run used different bench resources than last known good
  - this is a setup/change question first, not a health question

- Different digest and degraded instrument:
  - both changed
  - first confirm the new resource binding is intended
  - then investigate the health of the currently bound instrument

## Recommended Operator Output

When both are present, report them separately:

- `bench_drift`: current selection differs / does not differ from LKG
- `instrument_health`: current instrument healthy / degraded

Do not merge them into one vague "bench issue" line.

## Related Files

- [bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)
- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
- [bench_resource_drift_interpretation.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/bench_resource_drift_interpretation.md)
