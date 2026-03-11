# Validation Summary Emission Skill

## Purpose

`validation_summary_emission` is a lightweight AI skill specification for emitting a concise, decision-friendly summary after a successful run has completed validation.

Its job is to turn a successful execution result into a clear statement of:

- what was validated
- what passed
- what setup facts matter
- where the evidence lives
- what caveats still remain

It is a reporting skill specification, not a runtime feature.

## Why This Skill Matters

This is a high-value skill in AEL because:

- successful runs already produce meaningful structured result data
- users need a clear summary, not just raw logs or artifact paths
- this pattern repeats across board families and validation styles
- it helps make validated behavior easier to reuse and review
- it is already grounded in current standardized success output

## Trigger / When To Use

Use this skill when:

- a run has passed through `run` and `check`
- the user asks what was tested and what passed
- a successful result needs to be restated after a real run
- a validated path should be summarized before further changes or repeated use

## Inputs

Typical inputs include:

- successful `result.json`
- validation summary fields
- executed, skipped, and deferred stage information
- evidence and artifact references
- key passed checks
- current setup facts when available
- known caveats or cleanup items

Useful additional inputs may include:

- test plan identity
- instrument or control-instrument identity
- selected endpoint or port
- run-specific bench facts that matter for repeatability

## Preconditions And Assumptions

Reasonable assumptions:

- a run may be successful while still carrying caveats
- different validation paths may expose different kinds of checks
- some setup facts may be available only for some paths

What this skill should not assume:

- that success means the whole system is mature
- that all paths expose the same setup detail
- that a validation summary should replace detailed evidence files
- that caveats should be omitted because the run passed

This skill should keep separate:

- overall pass status
- executed and skipped stages
- key checks passed
- setup facts
- evidence paths
- caveats

## Core Flow

Recommended flow:

1. Inspect the successful run result.
2. Identify the board, test, and run id.
3. Summarize executed and skipped stages.
4. Summarize the key checks that passed.
5. Restate the most relevant setup facts.
6. Point to the key evidence and artifact paths.
7. Restate any caveats or cleanup items.
8. Present the result as a concise successful validation summary.

## Required Outputs

At minimum, this skill should produce:

- board and test
- run id
- overall result
- executed and skipped stages
- key checks passed
- important current setup facts when available
- evidence and artifact paths
- important caveats or cleanup items

A practical presentation shape is:

- Validation result
- Stages executed
- Key checks passed
- Current setup
- Evidence and artifacts
- Caveats

## Success Criteria

Successful execution of this skill means:

- the user can quickly understand what was validated
- passed checks are visible without log parsing
- relevant setup facts are easy to see
- evidence locations are easy to find
- caveats are not hidden
- the summary is more useful than a raw success log

## Non-Goals

This skill is not:

- a replacement for detailed run debugging
- a substitute for baseline or sequence-level review
- a full test report generator
- a guarantee that every related path is healthy
- a release-qualification summary

## Relationship To Adjacent Concepts

Relationship to `new_board_bringup`:

- this skill is one of the useful later-stage reporting patterns inside a successful bring-up flow

Relationship to `plan_stage_readiness_summary`:

- `plan_stage_readiness_summary` happens before real validation
- `validation_summary_emission` happens after successful validation

Relationship to `user_correction_and_setup_reprint`:

- setup correction happens before execution
- validation summary emission reports the successful result after execution

Relationship to `last_known_good_extraction`:

- validation summary reports the successful run outcome broadly
- `last_known_good_extraction` focuses more narrowly on the reusable successful setup state

## Near-Term Implementation Guidance

Without a formal skills system, this skill can already be used as:

- a documented output expectation after successful runs
- a prompt pattern for Codex or Gemini
- a review checklist for run result summaries
- a bridge between raw result artifacts and user-facing explanation

## Summary

`validation_summary_emission` is a strong current AEL skill candidate because it is already grounded in real successful run output and gives users a consistent, reusable explanation of what was actually validated.
