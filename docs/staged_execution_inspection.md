# Staged Execution Inspection (AEL)

## Current Status Before This Change

Staged execution already existed **partially** in code, but mostly as implicit boundaries:

- `plan` stage: implicit in `ael/pipeline.py` by building `plan_steps` and serializing `run_plan.json`.
- `pre-flight` stage: explicit step via `strategy_resolver.build_preflight_step(...)` with `preflight.*` adapter types.
- `run` stage: implicit in `build.*` and `load.*` steps executed by `ael/runner.py`.
- `check` stage: explicit step families (`check.signal`, `check.instrument_digital`, `check.uart`).
- `report` stage: implicit in final result/meta/evidence file writes in `ael/pipeline.py`.

What was missing:

- No simple user-facing switch to stop at a stage boundary in normal `ael run`.
- No consistent stage execution summary in outputs to show executed vs deferred stages.

## Existing Stage Outputs / Artifacts

- Plan artifact: `artifacts/run_plan.json`
- Runner result artifact: `artifacts/result.json`
- Top-level result summary: `result.json`
- Stage logs:
  - `preflight.log`
  - `build.log`
  - `flash.log`
  - `observe.log`
  - `verify.log`

## Minimal Implementation Added

Added a narrow, additive stage gate in the existing execution path:

- New CLI option on `ael run` and `ael.pipeline run`:
  - `--until-stage plan`
  - `--until-stage pre-flight` (alias `preflight` accepted)
  - default `--until-stage report` (full flow, unchanged behavior)

Execution behavior:

- `plan`:
  - Build and persist plan artifacts.
  - Execute no plan steps.
  - Emit report/result files with stage metadata.
- `plan + pre-flight`:
  - Execute only `preflight.*` steps from the generated plan.
  - Defer run/check stages.
- `report` (default):
  - Execute full existing flow.

Stage identity visibility:

- `plan["stages"] = ["plan", "pre-flight", "run", "check", "report"]`
- `plan["stage_execution"]` records requested boundary and executed/deferred stages.
- `result["stage_execution"]` mirrors the same summary.

## What Is Intentionally Not Done Yet

- No checkpoint/resume engine.
- No arbitrary stage graph execution.
- No new external phase model or renaming away from current AEL terms.
- No per-step resume pointer persistence beyond existing runner artifacts.

## Compatibility Notes

- Default behavior remains full flow (`report`) when `--until-stage` is not provided.
- Existing run/test strategy resolution and adapter model are unchanged.
