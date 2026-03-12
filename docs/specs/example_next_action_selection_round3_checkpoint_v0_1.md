# Example Next-Action Selection Round 3 Checkpoint v0.1

## Purpose

This checkpoint records the small Round 3 follow-on after runtime-readiness
classification and next-action selection were added.

## What Round 3 Added

- an execution-facing transition table for readiness-driven next actions:
  - [example_runtime_readiness_transition_table_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_runtime_readiness_transition_table_v0_1.md)
- an explicit link from the bounded next-expansion decision note to that
  transition table:
  - [next_example_expansion_decision_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/next_example_expansion_decision_v0_1.md)

## Why This Was The Right Follow-On

Rounds 1 and 2 established:
- runtime-readiness should be tracked separately from runtime-validation
- next-action selection should be readiness-aware

The remaining small gap was operational:
- what exact action should follow from each readiness state

This Round 3 addition closes that gap without adding new runtime churn.

## Current Practical Meaning

- `blocked_missing_bench_setup`
  - do not attempt live validation yet
- `blocked_unbound_external_input`
  - do not promote runtime claims until the input contract is defined
- `blocked_unstable_bench_path`
  - keep runtime claims conservative and treat live attempts as bounded bench
    observations
- `ready_now`
  - candidate for bounded live runtime validation

## Outcome

The generated-example governance path is now more complete:
- formal connection contract
- runtime-readiness classification
- next-action selection
- execution-facing state transition guidance

This is a better stopping point before attempting more generated-example
runtime work.
