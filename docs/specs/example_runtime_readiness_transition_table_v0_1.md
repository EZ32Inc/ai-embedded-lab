# Example Runtime Readiness Transition Table v0.1

## Purpose

This note turns the runtime-readiness model into an execution-facing table.

It answers:

> Given the current readiness state of a generated example, what is the right
> next action?

This is intentionally small and operational. It does not replace the broader
generation policy or runtime-readiness classification docs.

## States And Next Actions

### `ready_now`

Meaning:
- the generated example is formally complete for connection questions
- the current bench setup is sufficient for a meaningful live attempt

Allowed next action:
- attempt bounded live runtime validation

Do not:
- skip directly to broad family-level runtime claims

### `blocked_missing_bench_setup`

Meaning:
- the generated example is formally complete enough to describe
- but current bench provisioning is missing for a meaningful live attempt

Allowed next action:
- keep `plan` and `build` status as the strongest claim
- record the missing bench setup explicitly
- wait for bench provisioning before live runtime validation

Do not:
- treat the lack of live runtime validation as a generation defect

### `blocked_unbound_external_input`

Meaning:
- the generated example intentionally leaves one or more external inputs
  undefined in the current bench contract
- typical case: ADC examples without a defined external analog source

Allowed next action:
- keep the example as formally complete for current connection retrieval
- defer stronger runtime claims until the external input contract is defined

Do not:
- claim runtime readiness just because firmware and build are valid

### `blocked_unstable_bench_path`

Meaning:
- the generated example is formally complete and could be runnable in principle
- but the current bench path is unstable enough that runtime results would be
  distorted or non-repeatable

Allowed next action:
- keep runtime claims conservative
- allow bounded live attempts only when the result is still useful as a bench
  observation
- prefer fixing or waiting on the bench path before promoting validation state

Do not:
- treat repeated unstable-bench failures as proof that generation is wrong

## Transition Guidance

Common transitions:

- `blocked_missing_bench_setup -> ready_now`
  - occurs when the required UART or other bench path is actually provisioned

- `blocked_unbound_external_input -> ready_now`
  - occurs when the missing external input contract is defined and provisioned

- `blocked_unstable_bench_path -> ready_now`
  - occurs when the unstable bench dependency becomes stable enough for
    meaningful live validation

- `ready_now -> runtime_validated`
  - occurs only after a real bounded live validation attempt succeeds

## Current Typical Examples

- `rp2040_uart_banner`
  - current state: `blocked_missing_bench_setup`
  - next action: wait for UART bench provisioning

- `stm32f103_uart_banner`
  - current state: `blocked_missing_bench_setup`
  - next action: wait for UART bench provisioning

- `esp32c6_uart_banner`
  - current state: `blocked_unstable_bench_path`
  - next action: only bounded live attempts while meter path remains unstable

- ADC examples across families
  - current state: `blocked_unbound_external_input`
  - next action: define and provision external analog-source contract first

## Usage

Use this table with:
- [generated_example_runtime_readiness_review.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/generated_example_runtime_readiness_review.md)
- [generated_example_next_action_selection.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/generated_example_next_action_selection.md)
- [example_generation_catalog_v0_1.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_generation_catalog_v0_1.json)
