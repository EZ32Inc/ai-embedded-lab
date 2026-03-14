# Skill: Generate STM32-Family Example From Official Source And Local Reference

## Purpose

Add or expand STM32-family examples by combining:

- official STM32 source support for device/runtime facts
- the closest validated local AEL STM32 test methodology

This skill is for generated example paths, not only raw target bring-up.

## Scope

- STM32-family generated examples
- bounded STM32-family example expansion
- new STM32 board/example work where official ST source support already exists

## Core rule

For STM32-family generated examples, prefer:

1. official STM32 source support for device facts, startup/runtime basis, and
   memory/linker facts
2. the closest validated local AEL STM32 example as the methodology reference
3. official STM32 examples only as structural references when they materially
   help

Do not use board-example assumptions from ST packages as AEL board policy.
Do not treat an older STM32 target's register-level implementation as portable
to a first-time STM32 MCU unless official sources justify it.

## Inputs

- new board id and target id
- intended behavior, such as UART, GPIO, ADC, SPI, or I2C
- closest local validated STM32 AEL example
- official STM32 source basis used
- intended control-instrument path
- current wiring and bench assumptions

## Typical files to inspect and reuse

- `configs/boards/<reference>.yaml`
- `firmware/targets/<reference_target>/`
- `tests/plans/<reference_plan>.json`
- target-local `vendor/` files when official STM32 source is already present
- STM32 official-source policy and generation catalog

## Procedure

1. Confirm the official STM32 source basis that should govern:
   - startup/runtime facts
   - device headers
   - memory/linker facts
2. Identify the closest local STM32 AEL example for methodology reuse.
3. Perform a package/family drift check before code generation.
4. Keep AEL-owned behavior explicit:
   - UART ready banners
   - GPIO signature behavior
   - deterministic verification-friendly timing
5. If the example uses UART and the user has not specified UART settings, use
   the default UART configuration on both MCU and PC sides:
   - `115200`
   - `8N1`
6. Add or update:
   - board config
   - firmware target
   - test plan
   - provenance notes if official STM32 source material is copied or refreshed
7. Validate conservatively through:
   - `inventory describe-test`
   - `explain-stage --stage plan`
   - build-stage confirmation
   - runtime stages only when bench setup is ready

## Validation flow

1. Static file/path consistency.
2. `inventory describe-test --board <board> --test <test>`
3. `explain-stage --board <board> --test <test> --stage plan`
4. Build confirmation through AEL.
5. Runtime stages only when current bench setup is ready.

## Common pitfalls

- treating official STM32 examples as if they define AEL board wiring policy
- weakening provenance when mixing official STM32 source and local AEL examples
- promoting runtime claims when only plan/build checks have passed
- hiding missing runtime bench setup inside example generation status

## Outputs

- new STM32-family example target
- board config
- test plan
- provenance/validation notes
- explicit staged readiness summary

## Relationship to policies

- [stm32_official_source_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32_official_source_generation_policy_v0_1.md)
- [example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_generation_policy_v0_1.md)
- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
