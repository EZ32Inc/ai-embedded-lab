# Skill: Place STM32F401 External IRQ Handlers At The Correct Vector Index

## Trigger

Use this when:
- adding an interrupt-driven bare-metal self-test for STM32F401
- a timer or peripheral interrupt appears configured but mailbox status never leaves
  `RUNNING`

## Symptom

Typical failure:
- flash succeeds
- main starts
- mailbox stays `RUNNING`
- no PASS transition even though timer/NVIC registers look configured

## Root Cause Pattern

The handler can be placed at the wrong vector-table index.

For Cortex-M:
- core exceptions occupy the first 16 vector entries
- external IRQ `N` must be placed at entry `16 + N`

So for STM32F401:
- `TIM3_IRQHandler` for IRQ 29 must be at vector entry `45`

## STM32F401RCT6 Lesson

The first Stage 1 timer-mailbox attempt failed because the startup table was too
short and `TIM3_IRQHandler` was appended at the tail instead of the true IRQ 29
slot.

Fix:
- define the exception entries explicitly
- enumerate external IRQ entries until the needed IRQ
- place `TIM3_IRQHandler` at IRQ 29, not at an arbitrary final position

## Reusable Rule

For STM32 bare-metal interrupt tests:
- do not append a peripheral ISR to a shortened vector table
- compute the real vector index
- prefer explicit commented IRQ slots for the first interrupt-driven tests
