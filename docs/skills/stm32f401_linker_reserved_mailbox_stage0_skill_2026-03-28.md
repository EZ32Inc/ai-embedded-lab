# Skill: Use A Linker-Reserved Mailbox For STM32F401 Stage 0 Runtime Gates

## Trigger

Use this when:
- adding a mailbox-based bare-metal Stage 0 test for STM32F401
- the goal is a machine-verifiable SWD-only runtime gate
- no extra wiring should be required

## Rule

Do not place the mailbox at an arbitrary SRAM address without reserving it.

For STM32F401 Stage 0:
- reserve the mailbox block in the linker script
- lower `_estack` to the start of that reserved block
- point the test plan at the reserved mailbox base

## STM32F401RCT6 Implementation

Reserved mailbox region:
- `0x2000FC00–0x2000FFFF`

Implementation pieces:
- firmware target:
  - `firmware/targets/stm32f401rct6_minimal_runtime_mailbox/`
- linker:
  - `stm32f401_mailbox.ld`
- plan:
  - `tests/plans/stm32f401rct6_minimal_runtime_mailbox.json`

Mailbox contract:
- `magic = 0xAE100001`
- `status = RUNNING` on init
- `status = PASS` after deterministic settle
- `detail0` increments in idle loop after PASS

## Why

This avoids two common Stage 0 problems:
- stack collision with a guessed mailbox location
- proving only a visual effect instead of a machine-readable runtime gate

## Reusable Lesson

For STM32 bare-metal mailbox Stage 0 tests:
- reserve mailbox RAM explicitly
- keep the firmware minimal
- make the mailbox the proof, not the LED
- use the LED only as optional operator feedback
