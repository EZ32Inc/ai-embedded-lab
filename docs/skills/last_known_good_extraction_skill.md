# Last-Known-Good Extraction Skill

## Purpose

`last_known_good_extraction` is a lightweight AI skill specification for extracting or restating the reusable successful setup state from a passing run.

Its job is to make the last-known-good bench state easy to reuse by showing:

- which board and test passed
- which concrete setup facts were in effect
- which wiring assumptions mattered
- where the evidence for that successful state lives

It is a reporting skill specification, not a runtime feature.

## Why This Skill Matters

This is a high-value skill in AEL because:

- successful runs are more reusable when the setup state is explicit
- users often need to repeat a known-good path later
- it reduces loss of working bench knowledge between runs
- it complements validation summaries by focusing on reusable setup state
- it is already grounded in current `last_known_good_setup` output

## Trigger / When To Use

Use this skill when:

- a run has passed and the successful setup should be preserved or restated
- the user asks for the working setup of a passing path
- a known-good path should be repeated on the same bench
- a successful run should be turned into a reusable setup reference

## Inputs

Typical inputs include:

- successful `result.json`
- `last_known_good_setup`
- current setup facts when available
- relevant bench mapping or wiring assumptions
- evidence references from the successful run

Useful additional inputs may include:

- selected port
- selected AP or endpoint
- instrument or probe identity
- run id and artifact location

## Preconditions And Assumptions

Reasonable assumptions:

- a passing run may still have caveats
- some paths expose richer setup facts than others
- wiring may still be partially described as bench assumptions rather than universal board facts

What this skill should not assume:

- that one successful setup automatically generalizes to every bench
- that copied assumptions become universal truth just because one run passed
- that last-known-good should replace evidence or detailed results
- that every path will expose equally rich setup state

This skill should keep separate:

- confirmed successful setup facts
- still-contextual wiring assumptions
- evidence references
- caveats that may matter for reuse

## Core Flow

Recommended flow:

1. Inspect the successful run result.
2. Extract the board, test, and run id.
3. Extract the concrete successful setup facts.
4. Restate relevant wiring or bench assumptions.
5. Point to the evidence and artifact locations.
6. Restate any caveats that matter for repeating the setup.
7. Present the result as a concise last-known-good setup.

## Required Outputs

At minimum, this skill should produce:

- board and test
- run id
- relevant port, endpoint, AP, instrument, or probe facts when available
- relevant wiring or bench assumptions
- evidence location
- caveats that matter for reuse

A practical presentation shape is:

- Last-known-good identity
- Working setup facts
- Wiring / bench assumptions
- Evidence location
- Caveats for reuse

## Success Criteria

Successful execution of this skill means:

- the user can quickly reuse the working setup
- successful setup facts are explicit
- wiring context is visible
- evidence location is easy to find
- reuse caveats are not hidden
- the output is more useful than a raw artifact path or bare success acknowledgement

## Non-Goals

This skill is not:

- a replacement for full run results
- a generic bench inventory system
- a guarantee that the same setup will work unchanged on every bench
- a substitute for validation summary emission
- a full setup-state persistence framework

## Relationship To Adjacent Concepts

Relationship to `validation_summary_emission`:

- `validation_summary_emission` summarizes what was validated
- `last_known_good_extraction` focuses on the reusable working setup that produced that validation

Relationship to `new_board_bringup`:

- this skill is a useful late-stage reporting pattern after first successful bring-up

Relationship to `user_correction_and_setup_reprint`:

- user correction updates the working setup before execution
- last-known-good extraction restates the successful setup after execution

Relationship to board / test / instrument / `bench_setup` boundaries:

- setup facts and wiring assumptions should remain associated with the bench context that produced the pass
- they should not be generalized into board identity unless that is truly warranted

## Near-Term Implementation Guidance

Without a formal skills system, this skill can already be used as:

- a documented output expectation after successful runs
- a prompt pattern for Codex or Gemini
- a review checklist when restating a reusable passing setup
- a bridge between successful result artifacts and repeatable bench execution

## Summary

`last_known_good_extraction` is a strong current AEL skill candidate because it preserves the most reusable part of a successful run: the concrete setup state that actually worked on the bench.
