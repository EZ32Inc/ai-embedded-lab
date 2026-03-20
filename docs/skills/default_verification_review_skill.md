# Default Verification Review Skill

## Purpose

`default_verification_review` is a lightweight AI skill specification for interpreting the current default verification sequence and presenting a concise, decision-friendly review of baseline system health, current validated paths, failures or weak points, and the current confidence state of AEL.

Its job is to:

- restate what baseline paths were actually exercised
- summarize pass or fail state without forcing the user to parse raw logs
- surface important caveats or weak points
- communicate current baseline confidence clearly
- distinguish real failures from invalid non-bench runs

It is a workflow and reporting skill specification, not a runtime feature.

## Why This Skill Matters

This is a high-value skill in AEL because:

- default verification is now a real baseline confidence mechanism, not a placeholder
- it covers more than one board family and more than one validation style
- users need more than raw pass/fail logs
- AI should be able to summarize current baseline health clearly
- it helps preserve and communicate what currently works reliably

## Trigger / When To Use

Use this skill when:

- `python3 -m ael verify-default run` has just completed
- `python3 -m ael verify-default review` is available and can be used as the primary repo-native summary source
- the default verification sequence has changed
- a key board, test, or instrument path included in the sequence has changed
- the user asks whether the current baseline is healthy
- baseline confidence should be summarized before more architecture, workflow, or board changes are made

## Inputs

Typical inputs include:

- `python3 -m ael verify-default review`
- `python3 -m ael verify-default state --format json`
- current default verification settings
- the executed default verification sequence
- per-step run results
- validation summaries from the runs
- evidence and artifact references
- known caveats or intermittent issues
- current validated baseline context, if available

Useful additional inputs may include:

- last-known-good setup for sequence steps
- recent changes that affected one or more steps
- known reporting or formatting weaknesses that do not invalidate the run but still matter for interpretation

## Preconditions And Assumptions

Reasonable assumptions:

- default verification is a baseline confidence tool, not complete product coverage
- step-level results may use different validation styles
- a passing baseline may still have known caveats
- one failing step may have different significance depending on what part of the baseline it covers

What this skill should not assume:

- that “default verification passed” means everything in AEL is mature
- that all sequence steps are equally representative of total system health
- that raw pass/fail alone is enough context for decision-making
- that known caveats should be hidden just because the overall result passed

This skill should keep separate:

- overall baseline health
- per-step success or failure
- invalid runs with no real bench access
- known caveats or weak points
- current coverage gaps

## Core Flow

Recommended flow:

1. Run `python3 -m ael verify-default review` first.
2. If needed, inspect `python3 -m ael verify-default state --format json` for structured details.
3. Inspect the current default verification configuration when the review summary is not enough.
4. Inspect the executed sequence and per-step results.
3. Identify which board, test, and instrument paths were exercised.
4. Summarize the pass or fail state for each step.
5. Classify any sandbox-blocked or network-policy-blocked live-bench attempt as
   `INVALID`.
6. Summarize the overall baseline health.
7. Identify caveats, warnings, weak points, or partial limitations.
8. Restate the current baseline confidence in practical terms.
9. Present the recommended next interpretation or safe next action.

The output should stay concise, but it must be useful for deciding whether the current baseline is healthy enough to proceed.

## Required Outputs

At minimum, this skill should produce:

- current default verification sequence
- per-step result summary
- which board, test, and instrument paths were exercised
- overall baseline health assessment
- explicit distinction between `FAIL` and `INVALID` where relevant
- important caveats or known weak points
- recommended next interpretation or next safe action

A practical presentation shape is:

- Sequence exercised
- Per-step results
- Current baseline confidence
- Caveats / known weak points
- Recommended next step

## Success Criteria

Successful execution of this skill means:

- the user can quickly understand whether the current baseline is healthy
- the default verification sequence is clearly restated
- pass/fail is summarized without forcing the user to parse raw logs
- invalid non-bench attempts are not misreported as hardware failures
- caveats and weak points are not hidden
- the result is useful for deciding whether to proceed with more changes

## Non-Goals

This skill is not:

- a replacement for individual run debugging
- a substitute for full system test coverage
- a marketing summary
- a generic log dump
- a guarantee that all AEL paths are healthy
- a full release qualification system

## Relationship To Adjacent Concepts

This skill is a baseline-health review skill, not a board-bringup skill and not a low-level instrument skill.

Relationship to validation summary emission:

- validation summaries provide per-run successful execution details
- `default_verification_review` interprets the whole default baseline sequence across steps

Relationship to last-known-good setup:

- last-known-good setup helps restate known successful step setups
- `default_verification_review` uses those facts as supporting context, not as its primary output

Relationship to current validated capabilities baseline:

- this skill helps restate and confirm the current validated baseline in operational terms
- it complements [current_validated_capabilities.md](/nvme1t/work/codex/ai-embedded-lab/docs/current_validated_capabilities.md)

Relationship to instrument architecture status:

- instrument architecture influences how strong or mature the exercised paths are
- this skill may mention known instrument-side caveats, but it is not an architecture design skill

Relationship to `new_board_bringup`:

- `new_board_bringup` is about introducing and validating a new board path
- `default_verification_review` is about the health of the current baseline after those paths are in the sequence

Relationship to workflow/reporting skills more broadly:

- this skill sits above individual run summaries and interprets the current baseline as a sequence-level confidence signal

## Near-Term Implementation Guidance

Without a formal skills system, this skill can already be used as:

- a repo-native command pattern built around `python3 -m ael verify-default review`
- a documented output expectation after default verification runs
- a prompt pattern for Codex or Gemini
- a review checklist before or after structural changes
- a consistent way to restate current confidence after baseline runs

The near-term value is better sequence-level interpretation, not framework design.

## Summary

`default_verification_review` is a strong current AEL skill candidate because default verification is now a real validated baseline, and this skill turns that baseline from a raw sequence of run outputs into a clear statement of current system confidence, known strengths, and known limits.
