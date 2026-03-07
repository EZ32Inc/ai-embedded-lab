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

1. Copy board config from reference and update target identity fields.
2. Create minimal firmware target folder from reference IDF project.
3. Add minimal test plan(s) cloned from reference and update ids/tokens.
4. Add DUT manifest and docs with `verified: false` until hardware run completes.
5. Add DUT test asset manifest and firmware for GPIO/UART baseline.
6. If needed, generalize any hardcoded adapter target naming.
7. Add or update instrument manifest for expected AP/transport profile.
8. Write extension report capturing reused vs changed parts and friction.

## Typical Validation Flow

1. Static checks: file existence and path consistency.
2. Plan loading and board resolution checks.
3. Build-only check when toolchain is available.
4. Full run only after hardware bench is ready.

## Expected Evidence / Signs Of Success

- New board appears in CLI resolution path.
- New plan files resolve with no missing references.
- IDF build artifact lookup uses target-derived naming.
- DUT and test asset manifests are discoverable.
- Hardware validation can be started without structural code changes.

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
