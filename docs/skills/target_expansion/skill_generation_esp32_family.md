# Skill: Generate ESP32-Family Target From IDF Example

## Purpose

Add or expand ESP32-family targets by using the closest official ESP-IDF example
as the source basis, then adapting it into AEL target/example form.

## Scope

- ESP32-family target expansion
- ESP32-family example generation
- new ESP32-family board bring-up where ESP-IDF support already exists

## Core rule

For ESP32-family work, prefer:

1. official ESP-IDF example as the source basis
2. closest local validated AEL ESP32-family target as the structural reference
3. provisional AEL-owned minimal example only when no suitable IDF example
   exists

## Inputs

- new board id and target id
- intended behavior, such as GPIO golden/signature or UART-backed validation
- closest local ESP32-family AEL reference
- chosen ESP-IDF example path
- intended instrument or control-instrument path
- current wiring and pin assumptions

## Typical files to inspect and reuse

- `configs/boards/<reference>.yaml`
- `firmware/targets/<reference_target>/`
- `tests/plans/<reference_plan>.json`
- `assets_golden/duts/<reference_dut>/...`
- official ESP-IDF example sources for the selected behavior
- `ael/adapters/build_idf.py`
- `ael/adapters/build_artifacts.py`

## Procedure

1. Choose the closest official ESP-IDF example first.
2. Choose the closest local AEL ESP32-family target as the structural reference.
3. Adapt the example into `firmware/targets/<target>/`.
4. Keep AEL-owned behavior explicit:
   - UART ready markers
   - GPIO signature behavior
   - deterministic timing used by verification
5. If the example uses UART and the user has not specified UART settings, use
   the default UART configuration on both MCU and PC sides:
   - `115200`
   - `8N1`
   Tell the user that this default is being used and invite an override.
6. Add or update:
   - board config
   - test plan
   - DUT manifest/docs or provenance notes as needed
7. Keep validation status conservative.
8. Validate through:
   - `inventory describe-test`
   - `explain-stage --stage plan`
   - build-stage confirmation
   - `pre-flight` and runtime stages only when bench conditions are ready

## Validation flow

1. Static file/path consistency.
2. `inventory describe-test --board <board> --test <test>`
3. `explain-stage --board <board> --test <test> --stage plan`
4. build confirmation through AEL
5. `pre-flight`, `run`, and `check` when bench setup is ready

## Common pitfalls

- generating ESP32-family firmware from scratch when an IDF example already
  exists
- hiding board assumptions inside copied IDF code
- forgetting to align artifact names or project paths with AEL resolver
  expectations
- treating copied example code as already hardware-validated

## Outputs

- new ESP32-family target directory
- board config
- test plan
- provenance/validation notes
- staged readiness summary for follow-up bench work

## Relationship to policies

- [esp32_example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/esp32_example_generation_policy_v0_1.md)
- [example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_generation_policy_v0_1.md)
- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
