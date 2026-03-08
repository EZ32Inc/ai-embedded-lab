# AEL Skills Index

## Purpose

This document is the entry point for the current first batch of AEL skill specifications.

It is a short internal reference for:

- users
- Codex
- Gemini or other models
- future architecture and workflow work

These documents are lightweight skill specs, not a runtime system.

## Current Available Skill Specs

- [new_board_bringup](/nvme1t/work/codex/ai-embedded-lab/docs/skills/new_board_bringup_skill.md)
- [plan_stage_readiness_summary](/nvme1t/work/codex/ai-embedded-lab/docs/skills/plan_stage_readiness_summary_skill.md)
- [user_correction_and_setup_reprint](/nvme1t/work/codex/ai-embedded-lab/docs/skills/user_correction_and_setup_reprint_skill.md)
- [default_verification_review](/nvme1t/work/codex/ai-embedded-lab/docs/skills/default_verification_review_skill.md)

## One-Line Purpose For Each Skill

- `new_board_bringup`: guides a new DUT board from first introduction through structured bring-up toward first validated execution.
- `plan_stage_readiness_summary`: turns a successful `plan` stage into a clear readiness summary with assumptions, unknowns, and the next safe step.
- `user_correction_and_setup_reprint`: absorbs user corrections to setup assumptions and reprints the updated setup clearly before work continues.
- `default_verification_review`: interprets the default verification sequence as a baseline-health and confidence review.

## When To Use Which Skill

Practical situations:

- Adding a new board:
  use `new_board_bringup`

- After `plan` on a new or uncertain path:
  use `plan_stage_readiness_summary`

- After the user corrects setup assumptions:
  use `user_correction_and_setup_reprint`

- After `python3 -m ael verify-default run`:
  use `default_verification_review`

- When reviewing current baseline confidence:
  use `default_verification_review`

## Relationship Between The Current Skills

The current first batch has a simple structure:

- `new_board_bringup` is the higher-level bring-up workflow skill.
- `plan_stage_readiness_summary` is a key sub-skill inside that bring-up flow.
- `user_correction_and_setup_reprint` is another key sub-skill inside that bring-up flow.
- `default_verification_review` is a baseline and system review skill, not part of the bring-up chain.

## Current Limits

This current skill set is not:

- a skill runtime
- a dispatcher or registry
- a complete skill library
- the final shape of AEL skill formalization

## Near-Term Usage Guidance

These skill specs can already be used now as:

- prompt patterns for Codex or Gemini
- behavior and review checklists
- output expectations in recurring workflow situations
- lightweight references for future workflow and architecture work
