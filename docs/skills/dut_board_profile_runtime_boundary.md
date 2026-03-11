# DUT vs Board Profile Runtime Boundary

## Purpose

Explain how to interpret the boundary between `selected_dut` and `selected_board_profile` in current AEL runtime output.

## Scope

This applies to runtime summaries, stage explanation, inventory describe output, and workflow archive records.

## Background

AEL now emits separate canonical runtime objects:
- `selected_dut`
- `selected_board_profile`
- `selected_bench_resources`

Current execution is still more board-profile-driven than fully DUT-driven.

## Core Rule

Interpret the fields this way:
- `selected_dut`: target identity
- `selected_board_profile`: runtime/tool policy identity
- `selected_bench_resources`: bound external hardware/resources

## Required Observations

Collect:
- `selected_dut`
- `selected_board_profile`
- any compatibility `board` field only if older payloads are involved

## Interpretation Guide

Important meanings:
- `selected_dut.runtime_binding=board_profile_driven`
  means runtime behavior is still sourced mainly from board policy today
- `selected_board_profile.role=runtime_policy`
  means this object is the explicit source of build/flash/observe defaults

Do not treat board profile as DUT identity.
Do not treat DUT identity as the full source of runtime tool policy.

## Diagnosis Workflow

1. Identify the target from `selected_dut`.
2. Identify runtime policy from `selected_board_profile`.
3. Identify external dependencies from `selected_bench_resources`.
4. If output seems contradictory, check whether a legacy compatibility field is being read instead of the canonical objects.

## Current Known Conclusions

- the separation is now explicit in active runtime/report/archive outputs
- deeper DUT-first runtime refactoring is still bounded future work, not the current primary contract

## Related Files

- [dut_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/dut_model.md)
- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [inventory.py](/nvme1t/work/codex/ai-embedded-lab/ael/inventory.py)
