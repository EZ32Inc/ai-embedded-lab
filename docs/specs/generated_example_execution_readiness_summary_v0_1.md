# Generated Example Execution Readiness Summary v0.1

## Purpose

This note gives a compact operator-facing summary of the current execution
readiness state for generated examples.

It is intentionally smaller than the broader governance docs. The goal is to
answer one practical question:

> What is the first thing worth doing next, depending on which blocker we can
> remove?

## First Provisioning Action

Provision one UART runtime path for one generated example:

- `rp2040_uart_banner`, or
- `stm32f103_uart_banner`

Why:
- these are the strongest first execution candidates
- they are blocked mainly by missing runtime setup, not by generation quality

## First Contract-Completion Action

The first bounded ADC contract-completion step is now done for:

- `stm32f103_adc_banner`

Current next ADC-side contract candidate:

- `rp2040_adc_banner`

Why:
- this keeps removing real formal-contract blockers
- it improves example state without requiring immediate hardware execution

## First Observation-Only Family Path

Keep ESP32 generated examples conservative for now:

- `esp32c6_uart_banner`
- `esp32c6_adc_meter`
- `esp32c6_spi_banner`
- `esp32c6_i2c_banner`

Why:
- current instability is still concentrated in the meter-backed bench path
- generation/build status remains useful, but runtime promotion should stay
  conservative until the bench path is more stable

## Use With

- [generated_example_next_move_triage_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_next_move_triage_v0_1.md)
- [generated_example_execution_priority_buckets_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_execution_priority_buckets_v0_1.md)
- [generated_example_first_execution_enablement_batch_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/generated_example_first_execution_enablement_batch_v0_1.md)
