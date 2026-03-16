# STM32G431CBU6 bring-up

## User Goal

8-experiment validation suite matching F4 pattern

## Current Status

- status: `draft_capability_created`
- path_maturity: `inferred` (confidence: medium)
- target MCU: `stm32g431cbu6`
- closest mature AEL path: `stm32f401ce_draft`
- domain: `user_project_domain`
- project user: `local_user`

## Confirmed Facts

- User requested a project for stm32g431cbu6

## Assumptions

- Target MCU stm32g431cbu6 is in the same Group as stm32f401ce_draft but is not an exact match — a draft capability will be bootstrapped using stm32f401ce_draft as a Group reference

## Unresolved Items

- Is stm32g431cbu6 the exact MCU or approximate? Confirm full part number
- What board is this? (official devkit, custom PCB, eval board?)
- Where is the LED connected? Which pin?
- Which GPIO pins should be used for toggling?
- What debug/flash/instrument setup is available?

## Draft Capability Created

A draft capability scaffold has been created in `assets_branch/duts/stm32g431cbu6_draft/`.
Fill in all PLACEHOLDER fields before attempting to run.

## Required Fill-ins (PLACEHOLDER fields)

- What is the exact MCU part number and clock speed?
- What board is this? (official devkit, custom PCB, eval board?)
- Which instrument instance will be used for debug/flash?
- Where is the LED connected? Which GPIO pins?
- What are the bench_connections (MCU pin → instrument channel)?
