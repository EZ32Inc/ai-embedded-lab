# Rounds Execution and Review

## Purpose

Define a reusable workflow for executing multiple bounded rounds of work, with
regression checks and review checkpoints between rounds.

This skill is intended for shorthand requests such as:

- `2_round_review`
- `3_round_review`

The number indicates how many rounds to execute. Each round is normally planned
as a small fixed set of batches, such as five batches.

## When to use

Use this workflow when:

- the work is too large for a single batch set
- the user wants controlled progress with review points
- regression checks must happen between rounds
- the next round should depend on whether the previous round stayed healthy

Do not use this workflow for:

- one-off single-batch work
- broad rewrites with no bounded review points

## Required round structure

Each round should follow this order:

1. propose the round batches
2. execute the batches one by one
3. run the agreed regression gate at the end of the round
4. review the result
5. decide whether to continue to the next round

## Default batch shape

Unless the user specifies otherwise, use:

- `5` batches per round

Each batch should be:

- bounded
- internally coherent
- easy to validate

## Regression gate

At the end of each round, run the project-appropriate regression check.

For AEL shared/runtime work, the normal gate is:

```bash
python3 -m ael verify-default run
```

If the work is doc-only or otherwise clearly does not affect runtime/shared
behavior, the round may use a smaller validation set instead, but that should be
stated explicitly.

## Continue / stop rule

Continue to the next round only if:

- there is no new major architecture/runtime regression
- any failure is either expected or clearly bench-side/non-blocking
- the current direction still looks valuable

Stop and review before continuing if:

- the regression gate reveals a new repo-side problem
- the scope is drifting
- the next round should be changed based on what was learned

## What to record after each round

The post-round review should state:

- what was implemented
- what was validated
- whether the regression gate passed cleanly
- whether any failures were known bench-side issues or real repo issues
- what the next round should be

## Checkpoint naming

At the start of a multi-round sequence, define a checkpoint name.

The checkpoint name should be:

- short
- specific to the current theme
- reusable in later review requests

Examples:

- `local-instrument-layer-review checkpoint`
- `example-generation-tracking checkpoint`

## Recommended interaction pattern

When the user asks for a two-round or three-round review sequence:

1. list all planned rounds and their batches first
2. ask whether to go before starting execution
3. execute Round 1
4. run the round-end regression gate
5. if clean enough, continue to Round 2
6. repeat until the requested number of rounds is complete
7. finish with a review summary

## User-decision stop rule

During a multi-round sequence, stop and ask the user when:

- a design or scope decision is needed
- there is more than one reasonable next direction and the choice matters
- a regression result introduces a new repo-side concern
- a batch reveals a meaningful product/bench tradeoff that should not be guessed

Do not continue past that point until the user gives direction.

## Notes

- Prefer a durable workflow doc over ad hoc memory.
- Prefer bounded rounds over momentum-driven expansion.
- Use the regression gate as a decision point, not as a formality.
