# Generated Example Execution Enablement Phase v0.1

## Purpose

Define the next phase after Local Instrument Interface Phase 2 closeout.

This phase is execution-facing.
It is not another governance expansion phase and not another instrument-layer
refactor.

## Why This Is The Right Next Phase

The repo now has:

- bounded generated-example governance
- formal connection contracts
- readiness classification
- next-action and blocker grouping
- a closed bounded Local Instrument Interface Phase 2

The next useful work is to remove one real execution blocker at a time.

## Phase Goal

Move selected generated examples from:

- `build_and_plan_verified`

toward:

- contract-complete and execution-ready
- or runtime-validated where real bench setup exists

without pretending blocked examples are ready.

## First Candidate Work

Two bounded candidate directions are valid:

1. provision one UART runtime path for one RP2 or STM32 generated example
2. complete one ADC external-input contract for one generated ADC example

## Preferred Immediate Direction

If UART hardware provisioning is not available now:

- start with one ADC external-input contract completion batch

If UART hardware provisioning becomes available:

- start with one RP2 or STM32 UART runtime path first

## Not This Phase

Do not treat this phase as:

- broad USB example expansion
- broad new-vendor family expansion
- broad runtime validation across all generated examples
- another general governance phase
