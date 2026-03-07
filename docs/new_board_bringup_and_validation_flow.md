# New Board Bring-Up And Validation Flow

## Purpose

This flow standardizes how AEL introduces and first-validates a new board.

The goal is to make new-board bring-up:

- clear
- repeatable
- user-confirmable
- less dependent on implicit memory
- easier to reuse across future boards

This document is intended to guide both:

- future AEL product behavior
- future Codex execution behavior when extending the platform

It is based partly on lessons learned from the recent real ESP32-C3 success path, and partly on forward-looking standardization for future boards.

## Standard Stages

The recommended new-board bring-up flow is:

1. Board introduction
2. Minimal asset and config creation
3. `plan`
4. Plan-stage readiness summary
5. User correction and confirmation loop
6. `pre-flight`
7. `run`
8. `check`
9. Validation summary
10. Last-known-good setup

These stages should be treated as explicit product stages, not as ad hoc operator behavior.

## Stage Requirements

### 1. Board Introduction

At board introduction, AEL should identify:

- board id
- target family
- intended first test path
- intended instrument or probe dependencies
- any known assumptions carried over from a similar board

Required output:

- selected board identity
- selected reference board or source pattern, if any
- initial assumptions
- known unknowns
- recommended next action

### 2. Minimal Asset And Config Creation

The first board addition should create the minimum needed path so the board can enter the AEL flow coherently.

This usually includes:

- board config
- minimal firmware target or DUT asset
- test plan
- golden asset path if the board is entering a golden validation flow

Required output:

- files created or updated
- what each file is for
- any values copied from a similar board
- assumptions still not confirmed on real hardware

### 3. `plan`

`plan` is the first execution checkpoint.

Its job is not to prove hardware readiness. Its job is to prove that AEL can construct a coherent run plan for the new board.

Required output:

- whether `plan` executed successfully
- the selected board and test
- whether execution stopped at `plan` intentionally
- artifact location for the generated run plan

### 4. Plan-Stage Readiness Summary

For a newly added board, a successful `plan` stage must be followed by a structured readiness summary.

This is mandatory. AEL should not stop at “plan passed”.

The readiness summary should proactively show:

- selected board and test
- assumed instrument profile
- assumed endpoint
- current wiring assumptions
- expected observations and checks
- unresolved or unconfirmed items
- information still needed from the user
- recommended next step

This summary exists to let the user confirm or correct setup assumptions before real bench execution continues.

## Required Outputs By Stage

At every stage, AEL should separate:

- assumptions
- confirmed facts
- unresolved items
- user inputs still needed
- recommended next action

### Required stage outputs

For `plan`:

- board
- test
- assumed instrument profile
- assumed endpoint
- wiring assumptions
- expected checks
- unresolved items
- user inputs needed
- recommended next step

For `pre-flight`:

- whether executed, skipped, or failed
- probe or instrument readiness status
- serial or flash port assumptions versus confirmed values
- which checks are advisory versus required
- precise reason for any skip

For `run`:

- build result
- flash result
- observe result
- any stage-local assumptions still in effect

For `check`:

- which checks passed
- which checks failed
- which evidence files were produced
- whether failures are due to setup mismatch, runtime crash, missing signal, or unmet expectation

For final summary:

- pass or fail
- executed stages
- skipped stages
- key passed checks
- unresolved caveats
- evidence and artifact paths

## User Correction And Confirmation Loop

User correction is a normal and expected part of new-board bring-up.

AEL should:

- accept corrections from the user
- apply them explicitly
- reprint the updated setup clearly
- separate updated facts from remaining unknowns
- continue only after the corrected setup is clear

Typical corrections may include:

- board identity or revision
- serial port
- boot or reset behavior
- safe GPIO choices
- actual instrument profile
- actual endpoint
- actual bench wiring

After corrections, AEL should print:

- applied corrections
- updated confirmed facts
- remaining unknowns
- safe next step

## Pre-Flight Semantics

Pre-flight semantics must remain clean and consistent.

Rules:

- `skipped` must not be reported as `executed`
- report text and recorded stage state must match
- assumptions must remain distinct from confirmed facts
- advisory checks must remain distinct from required checks

If `pre-flight` is disabled by test configuration, AEL should say:

- `pre-flight: skipped by configuration`

and the recorded stage model should reflect that skip, not an executed stage.

## First Successful Validation Output

After the first end-to-end pass, AEL should emit a concise validation summary including:

- board
- test
- run id
- pass or fail
- executed stages
- key passed checks
- evidence files
- artifact paths
- known cleanup items or caveats

This is the first strong proof that the board is not only configured, but actually usable in the AEL flow.

## Last-Known-Good Setup

After a first successful validation, AEL should preserve or print a last-known-good setup summary.

This should include:

- board
- test
- serial or flash port
- instrument profile
- endpoint
- relevant wiring assumptions
- evidence or artifact location
- run id

This allows future work to start from a known-good bench state instead of reconstructing it from history.

## Success Criteria For A Newly Added Board

A new board bring-up is strong when:

- the `plan` stage produces a structured readiness summary
- user corrections can be applied and reprinted cleanly
- `pre-flight` behavior is clear and semantically correct
- `run`, `check`, and `report` behavior is coherent
- first end-to-end validation succeeds
- a last-known-good setup can be identified

Success is not only “plan passed”.

Success means the board has crossed from speculative support into a validated, user-understandable workflow.

## Generalization Goal

This flow is intended to apply broadly to future boards, not just ESP32-C3.

Board-specific details will vary, but the structure should remain stable:

- introduce board
- construct minimal path
- plan
- print readiness summary
- accept corrections
- validate readiness
- run and check
- summarize first success
- preserve last-known-good setup

## ESP32-C3 Lessons Versus Forward Standardization

### Learned from the recent ESP32-C3 success

- new boards need a stronger post-`plan` summary than a bare pass/fail result
- user correction is not an exception; it is part of normal bring-up
- hardware success depends on clearly separating assumptions from confirmed bench facts
- first end-to-end validation provides the right anchor for a last-known-good setup
- execution semantics need to stay precise, especially around skipped versus executed stages

### Forward-looking standardization

- all future new-board bring-up should emit a structured readiness summary after `plan`
- correction and confirmation should be treated as a first-class flow stage
- first successful validation should always end with a concise validation summary
- AEL should preserve a last-known-good setup summary for future reuse
- stage reporting should stay explicit, deterministic, and user-facing
