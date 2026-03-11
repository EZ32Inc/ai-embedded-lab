# Example Generation Policy v0.1

This document defines the repo-level AEL policy for generating new reusable
examples and example-backed validation paths.

## Scope

This policy applies to example generation across MCU families, including:

- ESP32-family
- STM32-family
- RP2-family
- future families such as TI, NXP, or others

It complements target-generation policy. It does not replace family-specific
policies where those are stronger or more specialized.

## Purpose

AEL example generation should produce:

- reviewable example firmware and plans
- clear provenance
- explicit validation status
- family-appropriate source selection
- reuse-friendly example paths for later board expansion

The goal is not just to create something that compiles once. The goal is to
make new examples consistent, explainable, and easy to validate through AEL.

## Example generation source order

Choose the source basis in this order:

1. `verified_local_example_first`
   - Reuse the closest locally validated AEL example when a close behavioral
     match already exists.

2. `official_example_or_support_second`
   - Use official vendor examples or official vendor support packages when they
     materially improve correctness or are the strongest family starting point.

3. `provisional_example_fallback`
   - Create a provisional AEL-owned example only when neither a local baseline
     nor a clean official example/support path exists.

## Family guidance

### ESP32-family

Prefer official ESP-IDF examples as the starting source basis, then adapt them
into AEL target/example form.

### STM32-family

Prefer official source support for device facts and startup/runtime support.
Examples may use official examples as structural references, but board
assumptions remain AEL-owned.

### RP2-family

Prefer the closest locally validated AEL RP2 example first.

For the first RP2350 path in a line, combine:

- official Pico SDK board/platform support
- closest local RP2040 AEL target/example shape

### New vendor families

For a first target/example in a new family, use a bounded hybrid approach:

- official vendor support or examples for device/runtime facts
- one explicit AEL-owned target/example shape
- conservative validation status

Once one validated baseline exists, later work should prefer local-reference-
first expansion.

## Required separation of concerns

Generated examples must keep these concerns distinct:

- official/vendor source basis
  - SDK/example/runtime/startup/device facts
- AEL-owned example behavior
  - GPIO signature logic
  - UART readiness
  - deterministic timing and verification glue
- board-specific assumptions
  - selected pins
  - bench wiring
  - control-instrument or instrument choice

## Required generated asset set

A coherent generated example path typically includes:

- board config
- firmware target or DUT firmware path
- test plan
- DUT manifest/docs or target-local provenance note as needed

The exact shape may vary by family, but the resulting AEL path must be
structurally complete enough for inventory and staged validation.

## Validation requirements

Generated examples must be validated conservatively and in stages:

1. static path and naming consistency
2. `inventory describe-test`
3. `explain-stage --stage plan`
4. build-stage confirmation
5. `pre-flight` when practical
6. full `run/check/report` only when bench conditions are ready

Do not claim runtime verification when only plan/build checks have been
completed.

Generated examples should also expose enough formal connection metadata that a
connection question can be answered from `describe-test`, the plan, and the
board profile without needing firmware inspection for the normal case.

## Provenance requirements

Generated examples should record:

- local reference example used, if any
- official vendor/example/support basis used, if any
- copied or structurally adapted files
- AEL-owned files
- important local deviations
- current validation status

## Working principles

- canonical family method first, ad hoc shortcuts second
- bounded adaptation over broad rewrites
- explicit provenance over implicit copying
- conservative validation claims
- one strong baseline before broad example expansion

## Relationship to family policies

Family-specific policies may specialize this document.

Examples:

- [esp32_example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/esp32_example_generation_policy_v0_1.md)
- [rp2_example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/rp2_example_generation_policy_v0_1.md)
- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
