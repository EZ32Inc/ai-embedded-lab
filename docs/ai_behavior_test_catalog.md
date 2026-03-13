# AEL AI Behavior Test Catalog

## Purpose

AEL now has important behaviors that are not only code behaviors. They are also AI-assisted retrieval, workflow, explanation, and skill-usage behaviors.

This catalog exists to make those behaviors testable and repeatable across versions.

Historical approved references can remain in the repo as archival evidence. They should be labeled as historical when they no longer represent the current live inventory or runtime output.

The goal is not exact text matching. The goal is to define whether the AI:

- used the correct formal retrieval path
- followed the expected workflow behavior
- included the required information
- avoided known failure modes
- produced a correct and grounded result

This is an internal engineering reference, not yet a full execution framework.

## What Kinds Of Things This Catalog Tests

The main categories are:

- inventory and coverage questions
- test-detail questions
- stage-semantics questions
- new-board bring-up behavior
- skill-guided workflow behavior
- baseline and default-verification review behavior

These are important because AEL now has formal retrieval paths and lightweight skill guidance that the AI should follow consistently.

## Organic Cases Vs Designed Cases

The catalog should support both:

### Organic cases

These come from real usage and real engineering work.

They are valuable because they reflect:

- what users actually ask
- where ambiguity really appears
- which behaviors actually matter in day-to-day development

### Designed cases

These are intentionally created to cover common, important, or high-frequency scenarios.

They are valuable because they help ensure:

- high-value behavior stays covered
- important version checks remain stable
- overnight evaluation runs can focus on known-critical workflows

Both kinds are important. Organic cases prevent the catalog from drifting away from reality. Designed cases improve coverage discipline.

## Recommended Structure Of A Test Case

Each behavior test case should stay lightweight and include:

- `case_id`
- `case_type` (`organic` or `designed`)
- `intent_type`
- `user_question`
- `possible_variants` (optional)
- `expected_retrieval_path`
- `expected_skill_guidance` (optional)
- `required_behavior`
- `required_output_elements`
- `forbidden_failure_modes`
- `judge_rubric`
- `notes`

This is enough structure to evaluate behavior without overbuilding a framework.

## What Should Be Tested Instead Of Exact Output Text

These cases should not mainly rely on exact-text comparison.

Reasons:

- natural language can vary
- wording may change across versions
- two correct answers may not use the same phrasing

What should be tested instead:

- whether the AI used the right retrieval path first
- whether the AI followed the expected behavior pattern
- whether the required information was present
- whether the answer stayed grounded in repo state
- whether known failure modes were avoided

When an approved reference is intentionally archival rather than live-current, the judge should preserve its historical meaning instead of trying to reconcile it with the latest repo state.

## Runner / Judge Idea

A future lightweight evaluation loop could look like this:

1. one AI run answers the case
2. another AI, or a structured AI review step, judges the response against the case contract
3. humans review important failures rather than every response manually

This is only a future direction.

This document does not define the full execution framework.

## Suggested Suite Levels

A simple layered view is enough for now:

### Quick sanity suite

Purpose:

- catch obvious regressions in high-frequency retrieval behavior
- run fast during frequent development checks

Example cases:

- current DUT inventory
- describe one test
- explain `plan`

### Common workflow suite

Purpose:

- check repeated important workflows across current AEL use
- cover skill-guided behavior and retrieval-path choice

Example cases:

- new-board bring-up handoff behavior
- setup correction behavior
- default verification review behavior

### Longer overnight suite

Purpose:

- cover broader designed and organic cases
- support version-to-version behavioral comparison
- include more ambiguous or multi-step cases

## First Example Cases

### Case: list current DUTs

- `case_id`: `inventory_current_duts_001`
- `case_type`: `designed`
- `intent_type`: `inventory_question`
- `user_question`: `What DUTs and tests do we currently have?`
- `expected_retrieval_path`: `python3 -m ael inventory list`
- `expected_skill_guidance`: none
- `required_behavior`:
  - use inventory command first
  - summarize DUTs and test names from generated repo state
- `required_output_elements`:
  - DUT ids
  - MCU names or families
  - test names
- `forbidden_failure_modes`:
  - manual repo search as the primary path when inventory exists
  - omitting covered DUTs
  - inventing unsupported DUTs
- `judge_rubric`:
  - pass if inventory command is used and the listed DUTs/tests match current repo state closely enough
- `notes`:
  - good quick sanity case

### Case: list tests for one board

- `case_id`: `inventory_board_tests_001`
- `case_type`: `designed`
- `intent_type`: `inventory_question`
- `user_question`: `What tests exist for stm32f401rct6?`
- `expected_retrieval_path`: `python3 -m ael inventory list`
- `expected_skill_guidance`: none
- `required_behavior`:
  - identify board-specific test coverage from inventory
- `required_output_elements`:
  - DUT id
  - tests for that DUT
- `forbidden_failure_modes`:
  - missing pack-linked tests
  - answering from stale memory
- `judge_rubric`:
  - pass if the response correctly reflects current generated inventory
- `notes`:
  - useful because pack-linked tests matter for STM32 paths

### Case: describe STM32F401RCT6 golden GPIO test

- `case_id`: `describe_test_stm32f401_001`
- `case_type`: `organic`
- `intent_type`: `test_detail_question`
- `user_question`: `Please show me stm32f401rct6 golden GPIO test connections and what will be tested info.`
- `expected_retrieval_path`: `python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/stm32f401_gpio_signature.json`
- `expected_skill_guidance`: none
- `required_behavior`:
  - use describe-test path first
  - summarize connections and expected checks
- `required_output_elements`:
  - probe or instrument identity
  - connections
  - expected checks
  - important limitation if only one signal is currently verified
- `forbidden_failure_modes`:
  - ad hoc reconstruction without using formal retrieval path
  - claiming multi-pin validation when only one signal is checked
- `judge_rubric`:
  - pass if the answer is grounded in describe-test output and explains the current test correctly
- `notes`:
  - directly grounded in recent AEL workflow

### Case: explain plan contents

- `case_id`: `explain_stage_plan_001`
- `case_type`: `organic`
- `intent_type`: `stage_semantics_question`
- `user_question`: `What's in plan?`
- `possible_variants`:
  - `What does plan include?`
  - `What does plan prove and not prove?`
- `expected_retrieval_path`: `python3 -m ael explain-stage --board <board_id> --test <test_path> --stage plan`
- `expected_skill_guidance`: `plan_stage_readiness_summary` if the question is part of new-board bring-up
- `required_behavior`:
  - use explain-stage first
  - separate selection/resolution behavior from real hardware confirmation
- `required_output_elements`:
  - selected board/test/probe or instrument
  - wiring assumptions
  - build/flash/check model selection
  - what plan does not confirm
- `forbidden_failure_modes`:
  - treating plan as real validation
  - blending assumptions with confirmed facts
- `judge_rubric`:
  - pass if the answer stays aligned with the explain-stage output and keeps stage semantics clean
- `notes`:
  - high-frequency stage question

### Case: explain pre-flight contents

- `case_id`: `explain_stage_preflight_001`
- `case_type`: `organic`
- `intent_type`: `stage_semantics_question`
- `user_question`: `What will be included in pre-flight?`
- `expected_retrieval_path`: `python3 -m ael explain-stage --board <board_id> --test <test_path> --stage pre-flight`
- `expected_skill_guidance`: none
- `required_behavior`:
  - explain what pre-flight checks probe or instrument readiness
  - explain what pre-flight does not prove
- `required_output_elements`:
  - enabled or skipped state
  - expected checks
  - confirms
  - does_not_confirm
- `forbidden_failure_modes`:
  - claiming pre-flight proves DUT behavior
  - ignoring skipped-by-config state
- `judge_rubric`:
  - pass if pre-flight semantics are accurately and clearly described
- `notes`:
  - useful because pre-flight meaning is often misunderstood

### Case: new board bring-up behavior

- `case_id`: `new_board_bringup_stm32f401_001`
- `case_type`: `organic`
- `intent_type`: `new_board_bringup`
- `user_question`: `Add a golden GPIO test for STM32F401RCT6 using ESP32JTAG as reference from STM32F103.`
- `expected_retrieval_path`:
  - repo inspection plus later formal retrieval paths as they become available
- `expected_skill_guidance`:
  - `new_board_bringup`
  - `plan_stage_readiness_summary`
  - `user_correction_and_setup_reprint` when relevant
- `required_behavior`:
  - create a coherent minimal path
  - avoid overtrusting stale STM32F103 details
  - run or prepare `plan`
  - make assumptions explicit
- `required_output_elements`:
  - files added or changed
  - selected wiring assumptions
  - what is still unvalidated
  - recommended next step
- `forbidden_failure_modes`:
  - pretending the F103 path is fully fresh and trusted
  - claiming full validation after only plan/build
- `judge_rubric`:
  - pass if the workflow follows the documented bring-up pattern and remains explicit about assumptions and gaps
- `notes`:
  - good organic case because it mixes implementation and workflow behavior

### Case: default verification review

- `case_id`: `default_verification_review_001`
- `case_type`: `designed`
- `intent_type`: `baseline_review`
- `user_question`: `What is currently covered and is the default verification baseline healthy?`
- `expected_retrieval_path`:
  - `python3 -m ael verify-default run` when a fresh run is requested
  - `default_verification_review` behavior for interpretation
- `expected_skill_guidance`:
  - `default_verification_review`
- `required_behavior`:
  - summarize per-step results
  - state overall baseline health
  - mention caveats or weak points
- `required_output_elements`:
  - sequence exercised
  - per-step results
  - current baseline confidence
  - caveats or limitations
- `forbidden_failure_modes`:
  - treating passing default verification as complete product maturity
  - hiding known caveats
- `judge_rubric`:
  - pass if the answer is sequence-aware, grounded, and caveat-aware
- `notes`:
  - important designed case for version checks

## Relationship To Existing Formal Retrieval Paths And Skills

This catalog should be anchored to the repo’s current formal retrieval paths and skill guidance.

Formal retrieval paths already available:

- `python3 -m ael inventory list`
- `python3 -m ael inventory describe-test ...`
- `python3 -m ael explain-stage ...`

Skill guidance already available:

- [README.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/README.md)
- [USAGE.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/USAGE.md)
- individual skill specs under `docs/skills/`

These give behavior tests something concrete to evaluate against. Without formal retrieval paths and skill docs, behavior cases would be much harder to judge consistently.

## Near-Term Recommendation

Recommended next step:

- keep this as a catalog only for now
- continue collecting both organic and designed cases
- use the catalog during important version checks
- only later decide which parts should become semi-automated or automated

The immediate goal is not a large eval system. The immediate goal is to make important AI-assisted behavior visible, named, and reviewable.

## Summary

This first AEL AI behavior test catalog is meant to make current AI-assisted retrieval, explanation, workflow, and skill-usage behavior explicit enough to evaluate repeatedly across versions, without overbuilding a framework too early.
