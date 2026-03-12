# Generated Example First Execution Candidates v0.1

## Purpose

This note identifies the first concrete execution candidates after the
generated-example governance and readiness work. It is intentionally
execution-facing and should remain smaller than the broader governance docs.

## First Execution Candidate If UART Setup Is Provisioned

- `rp2040_uart_banner`
- `stm32f103_uart_banner`

Reason:
- both are formally generated
- both have staged validation and build validation
- both are blocked mainly by missing UART bench setup, not by missing
  generation policy or missing connection-contract structure

## First Contract Candidate If No Setup Is Available

- define one explicit ADC external-input contract for one family/example

Recommended first target:
- `stm32f103_adc_banner`

Reason:
- ADC examples are formally complete enough to describe what is missing
- the next limiting factor is a real external analog-source contract
- this is a concrete contract-completion task, not a broad execution task

## First ESP32 Candidate That Should Remain Observation-Only

- `esp32c6_uart_banner`

Reason:
- the generated example is valid as a generation output
- but the current bench path remains coupled to the unstable meter-backed
  ESP32-C6 environment
- execution claims should remain conservative until that path is stable enough

## Not The First Things To Do

- broad USB example execution
- broad runtime validation across all generated examples
- new vendor-family expansion
- another governance-only pass

## Relationship To Existing Notes

This note is narrower than:
- `generated_example_execution_priority_buckets_v0_1.md`
- `generated_example_next_phase_handoff_v0_1.md`

It exists to answer one immediate planning question:
- what should we do first if we want to move from governance to execution?
