# AEL Skill Usage Guidance

## Purpose

This document explains how the current AEL skill specifications should be used now.

These skill documents are:

- prompt patterns
- behavior guides
- review checklists
- output expectations for recurring workflow situations

They are not a runtime system.

## What A Skill Spec Means Right Now

At the current AEL stage, a skill spec is a lightweight internal instruction document for recurring engineering workflows.

A skill spec should help an AI:

- recognize a repeated task pattern
- structure the response consistently
- surface the right assumptions, unknowns, and next steps
- avoid ad hoc behavior in repeated workflow situations

## How To Use The Current Skill Specs

Use these documents as:

- prompt patterns for Codex or Gemini
- response-shape guides in repeated workflow situations
- review checklists when checking whether an output is complete
- lightweight references when extending workflow documentation

## When A Skill Spec Should Influence Behavior

A skill spec should influence behavior when:

- the user request clearly matches the skill purpose
- the current workflow stage matches the skill trigger condition
- the same reporting or decision pattern has already repeated in AEL

Examples:

- inventory questions about DUTs, MCUs, or test coverage: use `python3 -m ael inventory list` first
- stage-semantics questions about `plan`, `pre-flight`, `run`, or `check`: use `python3 -m ael explain-stage ...` first
- adding a new board: use `new_board_bringup`
- after successful `plan`: use `plan_stage_readiness_summary`
- after user setup corrections: use `user_correction_and_setup_reprint`
- after successful run/check/report: use `validation_summary_emission`
- after a successful run when restating reusable bench state: use `last_known_good_extraction`
- after `verify-default run`: use `python3 -m ael verify-default review`, check `baseline_readiness_status`, then apply `default_verification_review`

## What Not To Do

Do not treat these docs as:

- a dispatcher design
- a plugin system
- a registry
- a full runtime framework
- a substitute for actual board, test, instrument, or bench-state implementation

Do not force a skill where the workflow does not fit.

## Selection Guidance

Use the smallest skill or set of skills that matches the real task.

Practical structure:

- high-level workflow skill:
  - `new_board_bringup`
- sub-skills inside that workflow:
  - `plan_stage_readiness_summary`
  - `user_correction_and_setup_reprint`
  - `validation_summary_emission`
  - `last_known_good_extraction`
- sequence-level review skill:
  - `default_verification_review`

## Relationship To Other AEL Docs

Skill specs should stay aligned with:

- workflow documents
- validated system behavior
- current config and boundary decisions

They should not drift into a parallel invented process.

## Near-Term Priority

Near-term, the main value of these skill specs is behavioral consistency.

The right next step is:

- use them consistently in recurring situations
- refine them when real workflow reveals gaps
- delay any runtime or framework formalization until boundaries are more stable
