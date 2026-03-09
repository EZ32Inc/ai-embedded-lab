# AEL AI Behavior Baseline v1

`AEL AI behavior baseline v1` is the first explicit approved AI behavior baseline set in the repo.

It turns the initial approved references into a named regression slice that can be run consistently without adding a large framework.

## Included Cases

- `inventory_current_duts_001`
  - capability: current DUT and test inventory retrieval
- `describe_test_stm32f401_001`
  - capability: repo-native per-test detail retrieval
- `explain_stage_plan_stm32f401_001`
  - capability: correct `plan` stage semantics
- `default_verification_review_001`
  - capability: current baseline-health review grounded in inventory plus default verification

## Why These 4 Cases

These were selected because they cover the first practical approved AI behavior surface for AEL:

- inventory
- detailed test description
- stage explanation
- default baseline review

That makes v1 small enough to run often, but broad enough to catch meaningful regressions.

## When To Run It

Run baseline v1:

- after changing AI behavior retrieval/reference tooling
- after changing inventory or stage explanation behavior
- after changing default verification review behavior
- before treating a new approved reference set as the next baseline

## How To Interpret Results

- `PASS`: current behavior matches the approved baseline cleanly
- `WEAK_PASS`: still acceptable, but changed enough to review
- `FAIL`: baseline behavior contract regressed
- `ERROR`: retrieval or judging failed before a meaningful comparison was completed

Baseline v1 is a lightweight regression baseline, not full AI behavior coverage for all AEL tasks.

## Run Command

```bash
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/baselines/v1.yaml
```
