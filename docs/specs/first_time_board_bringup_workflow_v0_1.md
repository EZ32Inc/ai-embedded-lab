# First-Time MCU / Board Bring-Up Workflow v0.1

This workflow defines the disciplined AEL bring-up path for a new MCU or board
that AEL has not supported before.

## Workflow principle

Reuse methodology, not old register-level assumptions.

For first-time MCU support:

- official vendor sources come first for implementation
- validated AEL patterns come first for test methodology

## Phase 1: MCU and board identification

Record:

- MCU part number
- board name or module name
- package name and package-specific constraints
- family/subfamily mapping
- whether this is a new MCU family for AEL or only a new board in a known
  family

Required outputs:

- confirmed identity facts
- unknown identity facts
- likely board family grouping

## Phase 2: Official-source anchoring

Collect and record the official source basis before implementation work.

Required source classes:

- datasheet
- reference manual
- programming manual if relevant
- official SDK/CMSIS package
- official startup/system files
- official peripheral examples for candidate first tests

Required outputs:

- selected official documents
- selected official SDK/package
- exact example families likely to guide GPIO/UART/ADC bring-up
- unresolved source gaps

## Phase 3: AEL methodology mapping

Select the closest previously validated AEL test methodology patterns.

Methodology examples may come from:

- STM32F103 GPIO signature
- STM32F103 UART banner
- STM32F103 ADC banner
- other validated non-STM32 AEL paths if the method is more relevant

This phase must record:

- which AEL tests are the methodology basis
- why those tests are structurally relevant
- which parts are methodology only
- which parts are not portable implementation details

## Phase 4: Pre-generation drift check

Perform a drift review before writing new target code.

Check:

- package pin availability versus reference board assumptions
- RCC/clock differences
- peripheral instance differences
- AF mapping differences
- memory/linker differences
- board-level boot/reset differences
- bench-connection differences

Required outputs:

- confirmed portable methodology pieces
- non-portable implementation pieces
- inferred items
- blockers that must be resolved first

## Phase 5: Minimum generation order

Generate in conservative order.

Recommended order:

1. target identity and provenance notes
2. official-source support package selection
3. minimal startup/system/linker basis
4. first GPIO bring-up path
5. first UART bring-up path
6. first ADC bring-up path
7. only then broader peripheral expansion

Do not generate many peripheral tests at once for a first-time MCU.

## Phase 6: Result classification

Each bring-up attempt must classify results as:

- pass
- fail
- partial
- blocked
- inferred_only

For each attempt, record:

- test attempted
- implementation basis used
- methodology basis used
- observed result
- likely cause class
- confidence level

## Phase 7: Lesson capture and write-back

After each meaningful bring-up round, update the reusable layer.

Write back:

- what succeeded
- what failed
- what was inferred
- what was learned
- what should be done differently next time

Write-back targets include:

- policy/spec docs
- workflow docs
- skill docs
- target-specific preparation docs

## Explicit rules

Do:

- use official sources as the implementation anchor
- reuse validated AEL test methodology
- label unknowns clearly
- stop and record drift before generating more code

Do not:

- copy old MCU code blindly
- treat old register-level implementation details as portable
- infer package-specific pin choices from another board without checking the new
  package
- treat passing `plan` as runtime validation

## Recommended minimum first-test order

For most new MCUs:

1. GPIO proof path
2. UART proof/banner path
3. ADC proof path
4. timer/EXTI/PWM/capture expansion
5. SPI/I2C once the lower-risk basics are stable

The exact order may change, but the first round should stay minimal and
evidence-driven.

## Required companion artifacts

Each new MCU bring-up should have:

- a preparation document
- a bring-up report
- provenance notes if vendor files are copied
- updated skill/workflow docs when a lesson is learned

## Relationship to adjacent docs

- [first_time_mcu_test_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/first_time_mcu_test_generation_policy_v0_1.md)
- [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)
