# AEL Skills (Minimum Framework v0.1)

A skill in AEL is a reusable, concrete engineering procedure derived from real extension work.

## Skill Types

- Target expansion: add a new board/target by reusing a known-good reference path.
- Capability expansion: add or evolve a capability across one or more existing targets.

## Skill States

- `candidate`: first draft from recent real work.
- `current`: recommended version for ongoing use.
- `deprecated`: still readable but not preferred.
- `obsolete`: retained only as historical context.

## Standard Outputs for Real Extension Work

- Golden path implementation.
- Extension report.
- Skill draft or skill update.
- Evidence baseline (validated and inferred parts clearly separated).
- Friction notes (what slowed or blocked extension).

## Staged Execution Alignment

For target-expansion work, explicitly track stage status with AEL terms:

- `plan`: structure, naming, and strategy consistency
- `pre-flight`: non-runtime readiness and bench/probe checks
- `run` / `check` / `report`: typically hardware-attached, may be intentionally deferred

## Required Post-Plan Communication For New DUTs

When a task adds or bootstraps a new DUT / board / MCU target and the work has reached `plan`, the AI should not stop at "plan passed" or "files were created".

If real bench wiring and runtime setup are not yet fully confirmed, the AI should proactively provide a structured post-`plan` handoff covering:

- current status by stage: `plan`, `pre-flight`, `run / check / report`
- available test names now created for the DUT
- current instrument profile assumption, including whether it is confirmed or placeholder
- current plan-level connection assumptions
- not yet confirmed hardware/runtime details
- concrete information still needed from the user
- one recommended next action

Use explicit labels such as `completed`, `assumed`, `not yet confirmed`, and `needed from user`.

Do not present plan-level wiring or instrument assumptions as validated hardware truth unless they have actually been confirmed during `pre-flight` or later stages.
