# Generated Example Pre-Execution Requirements v0.1

## Purpose

This note states what must exist before the first meaningful generated-example
execution batch can happen.

## UART Execution Batch Requirements

For the first RP2 or STM32 UART execution batch, the missing prerequisite is:

- one real UART bench path provisioned and confirmed

Minimum expectation:
- the DUT serial path is known
- the host-side serial instrument or direct console path is known
- the plan can be executed without guessing the UART connection

## ADC Execution Batch Requirements

For the first ADC execution batch, the missing prerequisite is:

- one explicit external analog-input contract

Minimum expectation:
- ADC input pin is formally identified
- external analog source is explicitly defined
- the connection contract states whether the path is ready or still blocked

## ESP32 Execution Requirement

For generated ESP32 execution claims, the constraint is different:

- current meter-backed runtime should remain conservative while the bench path
  is unstable

That means:
- generation/build claims are still valid
- runtime claims should not be promoted beyond what live results actually prove

## Working Rule

Do not start the first real generated-example execution batch until at least one
of these becomes true:

1. one UART runtime path is provisioned, or
2. one ADC external-input contract is explicitly completed
