# ESP32 Example Generation Policy v0.1

This document defines the ESP32-specific policy for generating new AEL example
firmware from ESP-IDF sources.

## Scope

This policy applies when adding or expanding ESP32-family example firmware and
example-backed validation paths in AEL.

It does not replace the general DUT target generation policy. It specializes
generation strategy for ESP32-family examples and example-backed targets.

## Purpose

For ESP32-family work, AEL should prefer ESP-IDF examples as the starting
source basis rather than generating firmware behavior from scratch.

The goal is to:

- keep ESP32-family support anchored to official Espressif target support
- reduce family-specific drift across ESP32 variants
- make provenance clearer
- keep generated examples easy to validate through AEL stages

## Preferred source order

Use source material in this order:

1. official ESP-IDF example for the closest matching behavior
2. closest locally validated AEL ESP32-family target/example
3. provisional minimal AEL-owned example only when no suitable IDF example
   exists

For common GPIO-style tests, prefer an official ESP-IDF example such as:

- `gpio`
- `blink`
- another small peripheral example with similar runtime behavior

Do not treat ad hoc hand-written firmware as the default starting point when an
IDF example already provides the correct family/runtime basis.

## Required separation of concerns

Generated ESP32-family examples must keep these concerns separate:

- ESP-IDF / vendor source basis
  - target support
  - startup/runtime behavior
  - build system structure
- AEL-owned example behavior
  - GPIO signature logic
  - UART ready tokens
  - deterministic timing or verification glue
- board-specific assumptions
  - chosen GPIO pins
  - wiring assumptions
  - bench/instrument expectations

Board-specific assumptions must not be hidden inside copied upstream example
code without clear AEL-owned adaptation.

## Generation rules

When generating a new ESP32-family example:

1. choose the closest official ESP-IDF example first
2. copy/adapt only the subset needed for the AEL target/example
3. keep the resulting firmware small and deterministic
4. add explicit AEL-owned behavior only where needed for verification
5. keep target ids, board ids, and artifact naming aligned with AEL resolver
   expectations

Expected AEL-owned additions often include:

- UART ready marker
- fixed GPIO pattern generation
- stable toggle/high/low timing for bench verification
- target-local naming/provenance notes

## Provenance requirements

ESP32-family example-based targets should record provenance clearly.

At minimum, provenance should include:

- upstream source basis
  - ESP-IDF repo/example path
- upstream version, tag, or local IDF basis used
- files copied or structurally adapted
- files that remain AEL-owned
- any behavior changes from the original example

If target-local `provenance.md` exists, use it. If a lighter local note is used
instead, the source basis must still be obvious from the target/example
directory and related docs.

## Validation requirements

Generated ESP32-family examples must be validated conservatively and in stages.

Required staged flow:

1. static path and naming consistency
2. `inventory describe-test`
3. `explain-stage --stage plan`
4. `run --until-stage pre-flight` when practical
5. full `run/check/report` only when bench conditions are ready

Do not present a generated ESP32-family example as runtime-validated when only
plan/build checks have completed.

## Example expansion expectations

For AEL, example generation and target generation are related but distinct.

- target generation answers:
  - can this ESP32-family board/target exist coherently in AEL?
- example generation answers:
  - can this board/target support a reusable validated example path?

When expanding ESP32-family coverage, prefer to:

1. establish the board/target coherently
2. establish one bounded example path from an IDF example
3. validate that path through AEL
4. only then expand additional examples

## Non-goals

This policy does not require:

- a full automatic generator
- broad copying of whole ESP-IDF example trees
- replacing all existing ESP32-family targets with freshly copied IDF examples

The goal is a clear and reviewable source policy, not automation for its own
 sake.

## Recommended current workflow

For a new ESP32-family board such as an ESP32-C3 GPIO example:

1. choose the closest ESP-IDF example
2. adapt it into `firmware/targets/<target>/`
3. add/update:
   - `configs/boards/<board>.yaml`
   - `tests/plans/<plan>.json`
   - DUT asset/provenance notes as needed
4. validate through `inventory`, `plan`, `pre-flight`, then runtime stages
5. record status conservatively until repeated hardware validation exists

## Relationship to other docs

- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
- [add_esp32_family_target_from_reference.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/target_expansion/add_esp32_family_target_from_reference.md)
- [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)
