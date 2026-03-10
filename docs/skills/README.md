# AEL Skills Index

## Purpose

This document is the entry point for the current first batch of AEL skill specifications.

It is a short internal reference for:

- users
- Codex
- Gemini or other models
- future architecture and workflow work

These documents are lightweight skill specs, not a runtime system.

Supporting guidance:

- [Skill Usage Guidance](/nvme1t/work/codex/ai-embedded-lab/docs/skills/USAGE.md)

## Current Available Skill Specs

- [new_board_bringup](/nvme1t/work/codex/ai-embedded-lab/docs/skills/new_board_bringup_skill.md)
- [plan_stage_readiness_summary](/nvme1t/work/codex/ai-embedded-lab/docs/skills/plan_stage_readiness_summary_skill.md)
- [user_correction_and_setup_reprint](/nvme1t/work/codex/ai-embedded-lab/docs/skills/user_correction_and_setup_reprint_skill.md)
- [validation_summary_emission](/nvme1t/work/codex/ai-embedded-lab/docs/skills/validation_summary_emission_skill.md)
- [last_known_good_extraction](/nvme1t/work/codex/ai-embedded-lab/docs/skills/last_known_good_extraction_skill.md)
- [default_verification_review](/nvme1t/work/codex/ai-embedded-lab/docs/skills/default_verification_review_skill.md)
- [ael_repo_answering](/nvme1t/work/codex/ai-embedded-lab/docs/skills/ael_repo_answering_skill.md)

## One-Line Purpose For Each Skill

- `new_board_bringup`: guides a new DUT board from first introduction through structured bring-up toward first validated execution.
- `plan_stage_readiness_summary`: turns a successful `plan` stage into a clear readiness summary with assumptions, unknowns, and the next safe step.
- `user_correction_and_setup_reprint`: absorbs user corrections to setup assumptions and reprints the updated setup clearly before work continues.
- `validation_summary_emission`: turns a successful run result into a concise explanation of what was validated and what passed.
- `last_known_good_extraction`: restates the reusable working setup from a successful run.
- `default_verification_review`: interprets the default verification sequence as a baseline-health and confidence review.
- `ael_repo_answering`: answers factual and operational AEL questions from the right formal source layer.

## When To Use Which Skill

Practical situations:

- Adding a new board:
  use `new_board_bringup`

- After `plan` on a new or uncertain path:
  use `plan_stage_readiness_summary`

- After the user corrects setup assumptions:
  use `user_correction_and_setup_reprint`

- After a successful run when summarizing what was validated:
  use `validation_summary_emission`

- After a successful run when restating the reusable working setup:
  use `last_known_good_extraction`

- After `python3 -m ael verify-default run`:
  use `default_verification_review`

- When reviewing current baseline confidence:
  use `default_verification_review`

- When answering questions like “What is AEL?”, “What is esp32jtag?”, or “How do you know this?”:
  use `ael_repo_answering`

## Relationship Between The Current Skills

The current first batch has a simple structure:

- `new_board_bringup` is the higher-level bring-up workflow skill.
- `plan_stage_readiness_summary` and `user_correction_and_setup_reprint` are key sub-skills inside that bring-up flow.
- `validation_summary_emission` and `last_known_good_extraction` are key post-success reporting skills.
- `default_verification_review` is a baseline and system review skill, not part of the bring-up chain.
- `ael_repo_answering` is a cross-cutting interpretation skill for factual and operational questions.

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
