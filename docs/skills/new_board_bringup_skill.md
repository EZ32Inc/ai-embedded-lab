# New Board Bring-Up Skill

## Purpose

`new_board_bringup` is a lightweight AI skill specification for guiding a new DUT board from initial introduction through first structured bring-up and toward first validated execution.

Its job is to make:

- assumptions explicit
- missing information visible
- user corrections easy to incorporate
- the next safe step clear

It is a workflow skill specification, not a runtime feature.

## Core source rule

For first-time MCU support:

- peripheral implementation should come primarily from official vendor sources
- test methodology should come primarily from previously validated AEL patterns

This skill should never treat an older target's register-level implementation
as automatically portable just because the validation method is reusable.

## Why This Skill Matters

This is one of the strongest current AEL skill candidates because:

- repeated real use already exists in recent ESP32-C3 and ESP32-C6 bring-up work
- future board expansion depends on this pattern
- it turns ad hoc bring-up into a structured repeatable flow
- it reduces hidden assumptions about ports, wiring, instrument choice, and expected checks
- it improves user clarity before bench execution moves forward

## Trigger / When To Use

Use this skill when:

- a new board is being added to AEL
- an existing board path is incomplete and needs structured bring-up
- a similar reference board exists and a new board path is being derived from it
- the user wants to run `plan`, `pre-flight`, or first validation on a newly introduced board
- the board/test/instrument path exists partially but assumptions still need to be surfaced and confirmed

## Inputs

Typical inputs include:

- new board identifier and human-readable board name
- target family or silicon family
- closest reference board or existing path, if any
- intended first test path, such as a golden GPIO signature test
- intended instrument or probe path
- known DUT-side constraints, such as safe GPIO choices, boot behavior, or flash size
- available user-provided bench facts, such as serial port, selected AP, wiring, or probe endpoint
- any prior validated path that should be reused rather than recreated

These inputs may be incomplete. The skill must tolerate that.

## Preconditions And Assumptions

Reasonable assumptions:

- a new board may start from incomplete information
- a similar reference board may be available
- the first useful checkpoint is usually `plan`, not full hardware validation
- some bench facts may remain unknown until the user confirms them

What the skill should not assume:

- that the serial port is already known
- that bench wiring is already confirmed
- that copied GPIO choices are definitely safe on the new board
- that the instrument profile or endpoint is already real bench truth
- that `plan` success means the board is validated

The skill should always distinguish between:

- assumed facts
- confirmed facts
- unresolved items
- user inputs still needed

## Core Flow

Recommended flow:

1. Identify the board and the nearest existing reference path.
2. Anchor implementation facts to official vendor sources.
3. Select the nearest validated AEL methodology pattern.
4. Perform a pre-generation drift review.
5. Create or clarify the minimum coherent board/test/asset/firmware path needed.
6. Run or prepare `plan` as the first execution checkpoint.
7. Emit the structured plan-stage readiness summary.
8. Surface unresolved items and the user inputs still needed.
9. Accept user corrections and reprint the updated setup clearly.
10. Continue to `pre-flight` when the setup is specific enough.
11. Continue to `run` and `check` when the path is ready.
12. After first success, emit the validation summary.
13. After first success, emit the last-known-good setup.
14. Write lessons back into the reusable skill/workflow/spec layer.

This flow should align with [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md).

## Required Outputs

At minimum, this skill should produce:

- files or paths created, updated, or intentionally reused
- the selected board, test, and reference path
- the current assumed board/test/instrument setup
- the structured plan-stage readiness summary when `plan` succeeds
- unresolved or unconfirmed items
- information still needed from the user
- updated setup after user corrections
- recommended next step
- validation summary after first successful run
- last-known-good setup after first successful validation

The plan-stage readiness summary should explicitly show:

- selected board and test
- assumed instrument profile
- assumed endpoint
- current wiring assumptions
- expected observations and checks
- unresolved items
- information needed from the user
- recommended next step

## Success Criteria

Successful execution of this skill means:

- the new board path is created or clarified in a structured way
- the nearest reference path is identified or the absence of one is made explicit
- assumptions are visible instead of hidden
- missing information is surfaced clearly
- user corrections can be incorporated cleanly
- the next safe step is obvious
- the path can move from `plan` toward first validation without chaotic ad hoc behavior
- after first pass, a clear validation summary and last-known-good setup exist

Success is not just “`plan` passed”.

## Non-Goals

This skill is not:

- a generic board auto-generator for every case
- a full autonomous hardware lab planner
- a runtime plugin, registry, dispatcher, or framework
- a replacement for instrument architecture work
- a substitute for user confirmation of real bench facts
- a guarantee of first-pass success on every board

## Relationship To Adjacent Concepts

This skill is a higher-level workflow pattern that depends on several adjacent concepts already present in AEL.

Relationship to workflow documents:

- it should follow the standard flow defined in [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)

Relationship to plan-stage readiness summary:

- this skill should invoke that pattern after successful `plan`
- it should not stop at “plan passed”

Relationship to user correction and setup reprint:

- this skill should treat user correction as a normal part of bring-up
- corrected facts should be restated clearly before continuing

Relationship to validation summary emission:

- after first successful execution, this skill should emit the standardized validation summary and last-known-good setup

Relationship to instrument boundaries:

- board identity, test intent, instrument profile, and bench setup should stay distinct
- bench facts such as ports, AP selection, and wiring should not be presented as already-confirmed board facts unless they are actually confirmed

## Near-Term Implementation Guidance

Without building a formal skills system, this skill can already influence AEL work as:

- a documented prompt pattern for Codex or Gemini
- a review checklist for new board additions
- a structured output expectation during board expansion work
- a lightweight spec that later formalization can build on

The right near-term use is behavioral consistency, not framework construction.

## Summary

`new_board_bringup` is one of the strongest current skill candidates in AEL because it is already grounded in real board expansion work, it maps directly to a repeated engineering workflow, and it improves clarity at the exact point where hidden assumptions otherwise create avoidable confusion.
