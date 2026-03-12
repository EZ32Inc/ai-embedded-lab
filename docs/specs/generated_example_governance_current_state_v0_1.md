# Generated Example Governance Current State v0.1

## Purpose

This note is a compact synthesis of the current generated-example governance
state after the recent readiness-driven review rounds.

It is meant to answer:

> What is the current state, and what should happen next without reopening the
> whole governance discussion?

## Current State

The repo now has:
- family-specific generation guidance
- example-generation policy
- formal connection-contract rules
- per-example catalog tracking
- runtime-readiness classification
- readiness-driven next-action selection
- an execution-facing readiness transition table
- family-level readiness/action summary
- an explicit governance stop boundary

## What Is Proven

- generated examples can be tracked conservatively without overstating runtime
  readiness
- blocked-by-setup, blocked-by-unbound-input, and blocked-by-unstable-bench are
  now distinct states
- next-action selection is now tied to those states instead of family strength
  alone

## What Is Still Blocking Progress

- missing UART/runtime bench provisioning for RP2 and STM32 generated runtime
  paths
- intentionally undefined external analog-input contracts for ADC paths
- unstable current meter-backed bench path for ESP32 generated-example runtime
  claims

## What Should Happen Next

Prefer one of:
- provision one least-blocked RP2 or STM32 generated runtime path
- define one concrete external analog-input contract for ADC
- keep ESP32 generated-example runtime claims conservative while the current
  bench path remains unstable

Do not prefer next:
- another broad governance pass
- broad USB expansion
- broad new-vendor family expansion

## Related Notes

- [generated_example_governance_stop_point_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_governance_stop_point_v0_1.md)
- [generated_example_next_execution_targets_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_next_execution_targets_v0_1.md)
- [example_family_readiness_action_summary_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_family_readiness_action_summary_v0_1.md)
