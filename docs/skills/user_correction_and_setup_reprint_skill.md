# User Correction And Setup Reprint Skill

## Purpose

`user_correction_and_setup_reprint` is a lightweight AI skill specification for absorbing user corrections to setup assumptions, updating the working setup state, and reprinting a clear, decision-friendly updated setup summary before work continues.

Its job is to:

- turn user feedback into explicit updated setup state
- prevent stale assumptions from silently propagating
- keep the user and AI aligned on the current setup
- make the next safe step clearer

It is a workflow skill specification, not a runtime feature and not a validation step.

## Why This Skill Matters

This is a high-value skill in AEL because:

- it turns user feedback into explicit updated setup state instead of vague acknowledgement
- it prevents stale assumptions about ports, APs, endpoints, wiring, or pin choices from persisting
- it keeps the user and AI aligned on what is currently assumed versus confirmed
- it is a natural bridge between post-`plan` clarification and later execution
- it reduces confusion during bring-up and bench setup work

## Trigger / When To Use

Use this skill when:

- the user corrects assumptions after a plan-stage readiness summary
- the user clarifies serial or flash port, AP choice, endpoint, wiring, or pin mapping
- copied assumptions from a reference board need to be replaced with real bench facts
- the current working setup has changed and should be restated before continuing
- a higher-level workflow such as `new_board_bringup` needs an updated setup handoff

## Inputs

Typical inputs include:

- current assumed setup summary
- user-provided corrections or confirmations
- selected board, test, and instrument path
- current `bench_setup` assumptions
- currently known confirmed facts
- unresolved items from the previous step

Useful additional inputs may include:

- prior reference-path assumptions that are being replaced
- current stage boundary, such as post-`plan` or pre-`run`
- known constraints that limit valid corrections, such as safe GPIO choices or required instrument channels

## Preconditions And Assumptions

Reasonable assumptions:

- the incoming setup state may be partially correct and partially wrong
- the user may correct only a subset of fields
- not every unresolved item will be resolved at once
- some setup facts may remain unknown until later bench interaction

What this skill should not assume:

- that all unresolved items will be solved in one correction round
- that corrected facts should be mixed back into unresolved assumptions
- that user correction implies validation has happened
- that unchanged assumptions should be treated as confirmed facts

This skill should explicitly keep separate:

- corrections applied
- updated confirmed facts
- remaining assumptions
- remaining unresolved items
- information still needed from the user

## Core Flow

Recommended flow:

1. Inspect the current assumed setup.
2. Parse the user corrections and confirmations.
3. Identify what changed and what did not.
4. Update the working setup state.
5. Move corrected items into confirmed facts.
6. Keep remaining assumptions separate from confirmed facts.
7. Restate remaining unresolved items.
8. Reprint the updated setup clearly.
9. Present the recommended next safe step.

The output should stay concise, but it must make the updated state easy to evaluate before execution continues.

## Required Outputs

At minimum, this skill should produce:

- applied corrections
- updated confirmed facts
- remaining assumptions, if any
- remaining unresolved items
- information still needed from the user, if any
- recommended next safe step

A practical presentation shape is:

- Corrections applied
- Updated confirmed setup
- Remaining assumptions
- Remaining unresolved items
- Information still needed
- Recommended next step

## Success Criteria

Successful execution of this skill means:

- the user can clearly see what changed
- stale assumptions are no longer presented as if still current
- corrected facts are explicit
- remaining unknowns are still visible
- the next safe step is clearer than before
- the updated output is more useful than a raw acknowledgement

## Non-Goals

This skill is not:

- a substitute for actual `pre-flight`, `run`, or `check` execution
- a guarantee that all setup issues are now solved
- a validation summary
- a generic chat acknowledgement
- a full bring-up skill by itself
- a replacement for future runtime state machinery

## Relationship To Adjacent Concepts

This skill is a reusable sub-skill that supports higher-level workflows.

Relationship to `new_board_bringup`:

- `new_board_bringup` is the broader workflow
- `user_correction_and_setup_reprint` is one of the sub-patterns that keeps the workflow aligned after user feedback

Relationship to `plan_stage_readiness_summary`:

- `plan_stage_readiness_summary` exposes the current assumptions and unknowns
- `user_correction_and_setup_reprint` absorbs the user's corrections and reprints the updated setup before work continues

Relationship to validation summary emission:

- this skill happens before validation
- it should not be confused with a post-success validation summary

Relationship to last-known-good setup:

- this skill updates the current working setup before validation
- last-known-good setup describes a known successful setup after validation

Relationship to board / test / instrument / `bench_setup` boundaries:

- corrected bench facts such as ports, AP choice, endpoint, and wiring should stay associated with setup state
- they should not be restated as intrinsic board facts unless they truly are board facts

## Near-Term Implementation Guidance

Without a formal skills system, this skill can already be used as:

- a documented output expectation after user correction
- a prompt pattern for Codex or Gemini
- a review checklist when setup facts change
- a reusable sub-pattern in new-board bring-up and bench setup workflows

The near-term value is consistent setup-state restatement, not framework design.

## Summary

`user_correction_and_setup_reprint` is a strong current AEL skill candidate because it turns user corrections into explicit updated setup state, prevents stale assumptions from propagating, and keeps higher-level bring-up and bench workflows aligned before execution continues.
