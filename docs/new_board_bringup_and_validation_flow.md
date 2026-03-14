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
2. Official-source anchoring and methodology mapping
3. Pre-generation drift check
4. Minimal asset and config creation
5. `plan`
6. Plan-stage readiness summary
7. User correction and confirmation loop
8. `pre-flight`
9. `run`
10. `check`
11. Validation summary
12. Last-known-good setup
13. New-board closeout validation
14. Lesson capture and write-back

These stages should be treated as explicit product stages, not as ad hoc operator behavior.

## Stage Requirements

### 1. Board Introduction

At board introduction, AEL should identify:

- board id
- target family
- intended first test path
- intended instrument or control-instrument dependencies
- any known assumptions carried over from a similar board

Required output:

- selected board identity
- selected reference board or source pattern, if any
- initial assumptions
- known unknowns
- recommended next action

### 2. Official-Source Anchoring And Methodology Mapping

At first-time MCU bring-up, AEL should record:

- official vendor documents and SDK support selected
- official example families selected as implementation references
- validated AEL tests selected as methodology references
- which reused local details are methodology only, not implementation truth

### 3. Pre-Generation Drift Check

Before generation, AEL should surface likely drift in:

- family/runtime support
- package pinout
- peripheral instances
- alternate-function mapping
- clocking
- memory layout
- bench setup assumptions

### 4. Minimal Asset And Config Creation

The first board addition should create the minimum needed path so the board can enter the AEL flow coherently.

Before minimal asset creation for a first-time MCU/board, AEL should explicitly
separate:

- implementation source
- test methodology source

Peripheral implementation should come primarily from official vendor sources.
Previously validated AEL paths should be reused primarily for methodology.

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

### 5. `plan`

`plan` is the first execution checkpoint.

Its job is not to prove hardware readiness. Its job is to prove that AEL can construct a coherent run plan for the new board.

Required output:

- whether `plan` executed successfully
- the selected board and test
- whether execution stopped at `plan` intentionally
- artifact location for the generated run plan

### 6. Plan-Stage Readiness Summary

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
- control-instrument or instrument readiness status
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
- serial or flash port, if known
- instrument profile, selected AP/SSID, and endpoint, when available
- evidence files
- artifact paths
- known cleanup items or caveats

This is the first strong proof that the board is not only configured, but actually usable in the AEL flow.

## New-Board Closeout Validation

After the first board suite is materially working, AEL should perform one more
explicit closeout pass before treating the board as integrated.

Required closeout actions:

- remove or isolate temporary diagnostics used only for bring-up
- rerun the cleaned full board suite on live hardware
- register the board as a DUT in inventory if it is intended to be a normal DUT
- decide whether one representative DUT-backed test should enter default
  verification
- if added, run live default verification to prove the new step resolves and
  executes in the baseline flow

Recommended default-verification choice:

- use one representative low-risk validated baseline test
- prefer the board-specific `gpio_signature`-style DUT test when available
- do not add the entire new suite to default verification by default

Required closeout output:

- full suite rerun result
- representative default-verification decision
- if added, live default-verification evidence
- updated bring-up closeout note

## Lesson Capture And Write-Back

After a first-time MCU bring-up round, AEL should record:

- what succeeded
- what failed
- what was inferred
- what was learned

These lessons should be written back into the reusable layer:

- skills
- workflow docs
- policy/spec docs
- target-specific preparation notes

## Last-Known-Good Setup

After a first successful validation, AEL should preserve or print a last-known-good setup summary.

This should include:

- board
- test
- serial or flash port
- instrument profile
- endpoint
- selected AP/SSID, when available
- relevant wiring assumptions
- evidence or artifact location
- run id

The user-facing validation output should stay concise and reuse existing run artifacts instead of dumping raw logs.

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
