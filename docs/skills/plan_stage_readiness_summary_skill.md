# Plan-Stage Readiness Summary Skill

## Purpose

`plan_stage_readiness_summary` is a lightweight AI skill specification for turning a successful `plan` stage into a clear, structured, decision-friendly readiness summary.

Its job is to make:

- current assumptions explicit
- unresolved items visible
- needed user confirmations clear
- the next safe step obvious

It is a workflow skill specification, not a runtime feature and not a validation step.

## Why This Skill Matters

This is a high-value skill in AEL because:

- it turns a bare “plan passed” message into something decision-useful
- it reduces user confusion about what is assumed versus what is confirmed
- it supports new-board bring-up and uncertain setup situations
- it is reusable across multiple boards, instruments, and bench configurations
- it helps prevent blind progression from `plan` into `pre-flight` or `run`

## Trigger / When To Use

Use this skill when:

- `plan` has succeeded on a newly added board
- `plan` has succeeded but setup facts are still incomplete
- bench wiring, port, instrument, or endpoint assumptions still need confirmation
- the next step should not proceed blindly after `plan`
- a higher-level workflow such as `new_board_bringup` needs a structured post-`plan` handoff

## Inputs

Typical inputs include:

- selected board
- selected test
- selected or assumed instrument profile
- selected or assumed endpoint
- current `bench_setup` or wiring assumptions
- expected observations or checks from the selected path
- stage boundary and `plan` result
- unresolved items already known
- any user-provided confirmed facts already available

Useful additional inputs may include:

- reference board or source path
- known board constraints, such as safe GPIO choices or boot quirks
- whether `pre-flight` is enabled, skipped, or deferred by configuration

## Preconditions And Assumptions

Reasonable assumptions:

- `plan` may succeed while many real bench facts remain unknown
- the selected path may still contain copied assumptions from a reference board
- some facts may be known only at the bench, such as serial port, AP choice, or actual wiring

What this skill should not assume:

- that real validation has happened
- that assumed setup facts are confirmed truth
- that a valid `plan` means the bench setup is correct
- that executed, skipped, and deferred stages can be blurred together

This skill should explicitly keep separate:

- assumed facts
- confirmed facts
- unresolved items
- user inputs still needed
- executed, skipped, and deferred stage concepts

## Core Flow

Recommended flow:

1. Inspect the `plan` output and the selected board/test path.
2. Collect currently known setup facts from the selected path and any user-provided confirmations.
3. Separate assumed facts from confirmed facts.
4. Restate the current wiring or `bench_setup` assumptions.
5. Restate the expected observations and checks.
6. Identify unresolved or unconfirmed items.
7. Identify the information still needed from the user.
8. Present the recommended next safe step.
9. Optionally call out likely risk points, such as copied GPIO assumptions or unconfirmed bench wiring.

The output should stay concise, but it must be concrete enough for the user to act on.

## Required Outputs

At minimum, this skill should produce a structured readiness summary including:

- selected board and test
- selected or assumed instrument profile
- selected or assumed endpoint
- current wiring or `bench_setup` assumptions
- expected observations and checks
- confirmed facts, if any
- unresolved or unconfirmed items
- information still needed from the user
- recommended next safe step

A practical presentation shape is:

- Current assumed setup
- Confirmed facts
- Expected observations and checks
- Unresolved items
- Information needed from user
- Recommended next step

## Success Criteria

Successful execution of this skill means:

- the user can quickly understand the current planned setup
- assumptions are visible instead of implicit
- missing information is visible
- real bench facts are not falsely implied
- the next safe step is obvious
- the output is meaningfully more useful than a raw engineering log or bare “plan passed” message

## Non-Goals

This skill is not:

- a substitute for actual `pre-flight`, `run`, or `check` execution
- a guarantee that the setup is correct
- a validation summary
- a generic logging dump
- a replacement for user confirmation of real bench facts
- a full board bring-up skill by itself

## Relationship To Adjacent Concepts

This skill is a smaller reusable sub-skill that supports higher-level workflows.

Relationship to `new_board_bringup`:

- `new_board_bringup` is the broader workflow
- `plan_stage_readiness_summary` is one of its key sub-patterns after successful `plan`

Relationship to user correction and setup reprint:

- this skill prepares the decision surface that the user can confirm or correct
- after correction, a separate setup reprint pattern should restate updated facts

Relationship to validation summary emission:

- this skill comes before real validation
- it should not be confused with a post-success validation summary

Relationship to last-known-good setup:

- this skill is about planned readiness before validation
- last-known-good setup is about known successful setup after validation

Relationship to workflow documents:

- this skill should follow the post-`plan` expectations documented in [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)

Relationship to board / test / instrument / `bench_setup` boundaries:

- board identity, test intent, instrument profile, and concrete bench setup should stay distinct
- copied bench assumptions should not be restated as confirmed board facts

## Near-Term Implementation Guidance

Without a formal skills system, this skill can already be used as:

- a documented output expectation after successful `plan`
- a review checklist for post-`plan` responses
- a prompt pattern for Codex or Gemini
- a reusable sub-pattern inside `new_board_bringup`

The near-term value is consistency of behavior, not framework design.

## Summary

`plan_stage_readiness_summary` is one of the strongest current skill candidates in AEL because it turns a technically successful `plan` into a user-usable decision point, keeps assumptions and unknowns visible, and supports safer progression into real bench execution.
