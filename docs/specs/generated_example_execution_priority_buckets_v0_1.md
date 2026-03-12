# Generated Example Execution Priority Buckets v0.1

## Purpose

This note groups the current generated-example work into a small number of
execution-facing priority buckets.

It answers:

> Which generated-example tasks are worth doing first, which are valuable but
> blocked, and which should be deferred?

## Bucket 1: First Execution Candidates

These are the best next execution targets once limited bench provisioning effort
is available.

- one RP2 generated UART runtime path
- one STM32 generated UART runtime path

Why:
- structurally strong
- blocked mainly by missing bench setup rather than generation quality

## Bucket 2: Valuable But Still Blocked

These are worthwhile, but they require one explicit missing contract or setup
step before runtime claims should advance.

- ADC examples needing a defined external analog-source contract
- RP2/STM32 generated SPI/I2C runtime paths that still depend on setup work

## Bucket 3: Conservative Observation Only

These can still be useful, but runtime claims should remain conservative while
the current bench path is unstable.

- ESP32 generated examples on the current meter-backed path

Why:
- current instability is still more bench-side than generation-side

## Bucket 4: Explicitly Deferred

Do not prioritize yet:

- broad USB example expansion
- broad new-vendor family generation
- broad runtime validation across all generated examples
- more governance layering for already understood blockers

## Use With

- [generated_example_execution_handoff_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_execution_handoff_v0_1.md)
- [generated_example_next_execution_targets_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_next_execution_targets_v0_1.md)
- [generated_example_governance_current_state_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_governance_current_state_v0_1.md)
