# Skill: Add ESP32-Family Target From Reference

## Purpose

Add a new ESP32-family target quickly and safely by deriving from an existing known-good ESP32 target.

## Scope

- Target-expansion skill for ESP32-family MCUs.
- Best for minimal phase-1 support before deeper hardware optimization.

## Inputs

- New target id and board id (example: `esp32c6`, `esp32c6_devkit`).
- Reference target path (example: `esp32s3_devkit`).
- Expected firmware/build system (`idf`).
- Initial DUT/instrument wiring assumptions.

## How To Choose The Best Reference Target

- Same toolchain first (`idf` before anything else).
- Same verification style (GPIO signature + UART banner).
- Same instrument interaction model, if present.
- Prefer the most recently validated target in that family.

## Typical Files To Inspect And Reuse

- `configs/boards/<reference>.yaml`
- `firmware/targets/<reference_target>/...`
- `tests/plans/<reference_plan>.json`
- `assets_golden/duts/<reference_dut>/manifest.yaml`
- `assets_golden/duts/<reference_dut>/<test_asset>/...`
- `ael/adapters/build_idf.py`
- `ael/adapters/build_artifacts.py`

## Typical Fields That Must Change

- Target/board identifiers.
- Build project names/paths.
- UART readiness token strings.
- Flash target naming if adapter defaults are too specific.
- Instrument id and AP naming if using new meter hardware profile.

## Procedure

1. Inspect existing draft work first; do not recreate from scratch unless broken.
2. Lock reference target set (`configs/boards`, `tests/plans`, DUT asset manifests, firmware target folder).
3. Normalize naming/path consistency at plan level:
   - board id
   - target id
   - build project path
   - expected artifact naming
4. Keep `verified: false` in DUT manifest until hardware stages complete.
5. Confirm adapters do not hardcode old target artifact names.
6. Run staged `plan` execution to confirm plan assembly/selection works.
7. Run staged `pre-flight` execution to validate probe + host-side readiness as far as practical.
8. Update extension report and metadata with explicit stage completion/defer decisions.
9. After `plan` completes for a new target, provide the user-facing post-plan handoff before waiting for follow-up questions.

## Typical Validation Flow

1. Static checks: file existence and path consistency.
2. Stage `plan`: `ael run --until-stage plan`.
3. Stage `pre-flight`: `ael run --until-stage pre-flight`.
4. Host-side target readiness check (for IDF targets): `idf.py ... set-target <target> reconfigure`.
5. Defer `run/check/report` hardware stages until bench setup is confirmed.

## Expected Evidence / Signs Of Success

- New board appears in CLI resolution path.
- New plan files resolve with no missing references.
- IDF build artifact lookup uses target-derived naming.
- DUT and test asset manifests are discoverable.
- `--until-stage plan` succeeds for new target path.
- `--until-stage pre-flight` succeeds (or fails with clear environmental reason).
- Hardware validation can be started later without structural code changes.

## Common Pitfalls (Observed/Expected In ESP32-C6 Case)

- Hidden hardcoded filenames tied to old target names.
- Prematurely marking a target as verified before bench run.
- AP SSID assumptions not matching real instrument firmware.
- Reusing reference pin notes without explicitly marking assumptions.

## Outputs

- New target board config + firmware + plans.
- DUT manifests/docs + test asset firmware path.
- Extension report.
- Skill metadata entry (candidate state).
- Explicit stage status: completed (`plan`, `pre-flight`) vs deferred (`run`, `check`, `report`).
- User-facing post-`plan` summary for new DUT work with:
  - current status
  - available test names
  - current instrument profile
  - current plan-level connection assumptions
  - not yet confirmed items
  - information needed from the user
  - recommended next action

## Required Post-Plan Handoff

When this skill is used for a new DUT and only `plan` is complete or confidently complete, the AI should proactively include a concise structured handoff. Use this shape:

## Current status
- `plan`: complete / partial
- `pre-flight`: not yet run / partial / complete
- `run / check / report`: deferred / not run

## Available test names
- ...

## Current instrument profile
- profile / manifest / endpoint:
- confirmed vs placeholder:

## Current plan-level connection assumptions
- ...

## Not yet confirmed
- ...

## Information needed from the user
- ...

## Recommended next action
- ...

The handoff must distinguish assumed wiring and placeholder instrument identity from validated bench facts.
