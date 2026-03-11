# Degraded Bench vs Execution Issue Review

## Purpose

Help distinguish bench-side degradation from an AEL execution-model defect.

## Scope

Use this when:
- one worker fails and others continue
- a run appears slow or "stuck"
- an unstable instrument path raises questions about whether AEL is at fault

## First Checks

1. Did unrelated workers continue and finish?
2. Did the failing worker reach the same stage consistently?
3. Is the failure classified as bench/instrument-side?
4. Did workflow events show normal run start and run finish?

## Strong Signs Of Bench-Side Degradation

- meter/instrument unreachable or API timeout
- UART-ready confirmed, then instrument verify timed out
- unrelated workers pass in the same suite
- run artifacts show normal stage progression up to the failing instrument step

## Strong Signs To Reopen Execution Investigation

- workers stop making progress without run completion artifacts
- unrelated workers block without a real shared resource
- wait logging points to an incorrect shared-resource claim
- summary/results flatten or contradict the actual artifact evidence

## Recommended Output

Report separately:
- `execution_model_status`
- `bench_or_instrument_status`

Do not collapse both into a generic "AEL failed" statement.

## Related Files

- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
- [default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)
- [roadmap_driven_ai_development.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/roadmap_driven_ai_development.md)
