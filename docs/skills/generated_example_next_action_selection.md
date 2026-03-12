# Generated Example Next Action Selection

## Purpose

Define how to choose the right next action for a generated example once plan,
build, and runtime-readiness information are already available.

## Use this when

- a generated example already exists
- the question is no longer "can we generate it?"
- the question is "what should we do next?"

## Decision order

1. check formal connection completeness
2. check runtime-readiness status
3. check actual runtime-validation status
4. choose the smallest next meaningful action

For the execution-facing readiness state machine behind this selection flow, see:
- [example_runtime_readiness_transition_table_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_runtime_readiness_transition_table_v0_1.md)

## Action map

### If the example is not formally complete

Next action:

- fix the formal connection contract first

Do not:

- attempt live runtime validation

### If the example is formally complete but `blocked_missing_bench_setup`

Next action:

- document the missing setup explicitly
- do not attempt live runtime validation yet
- continue only with governance/spec work or another example path

### If the example is formally complete but `blocked_unbound_external_input`

Next action:

- either define the missing external-input contract
- or keep runtime claims deferred

Do not:

- promote runtime status on the basis of build success alone

### If the example is formally complete but `blocked_unstable_bench_path`

Next action:

- keep runtime claims conservative
- treat live attempts as observational rather than promotive unless the bench
  becomes stable enough

### If the example is `runtime_ready_now` and `runtime_validation_status=not_run`

Next action:

- attempt one bounded live validation

### If the example is `runtime_ready_now` and already hardware-verified

Next action:

- only widen coverage if there is concrete value

## Working rule

Prefer:

- the least blocked example path
- the smallest next meaningful action

Avoid:

- forcing live validation on a blocked path
- treating governance churn as progress when the next real need is bench setup
