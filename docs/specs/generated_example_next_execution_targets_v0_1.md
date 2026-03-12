# Generated Example Next Execution Targets v0.1

## Purpose

This note records the next practical execution targets after the current
generated-example governance work.

It is intentionally execution-facing:
- not another policy layer
- not another family review

It answers:

> If we stop governance churn now, what should we actually do next?

## Next Practical Targets

### 1. Provision one UART runtime path for RP2 or STM32

Why:
- generated UART examples for RP2 and STM32 are structurally strong
- they are blocked mainly by missing bench setup, not by generation quality

Target outcome:
- move one generated UART example from `blocked_missing_bench_setup`
  toward `ready_now`

### 2. Define one real external analog-source contract for ADC

Why:
- ADC examples are formally complete enough to answer connection questions
- stronger runtime claims are still blocked by intentionally unbound external
  analog input

Target outcome:
- move one ADC path from `blocked_unbound_external_input` toward `ready_now`

### 3. Keep ESP32 generated-example claims conservative

Why:
- current ESP32 generated examples are more limited by the unstable meter-backed
  bench path than by generation quality

Target outcome:
- keep bounded observations only
- avoid overstating runtime validation while the bench path remains unstable

## Not The Next Targets

Do not prioritize next:
- more governance layering
- broad USB example expansion
- broad new-vendor family generation
- broad runtime validation across all generated examples

## Use With

- [generated_example_governance_stop_point_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_governance_stop_point_v0_1.md)
- [example_family_readiness_action_summary_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_family_readiness_action_summary_v0_1.md)
- [next_example_expansion_decision_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/next_example_expansion_decision_v0_1.md)
