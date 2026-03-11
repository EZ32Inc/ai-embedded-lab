# RP2 Example Generation Policy v0.1

This document defines the current AEL policy for generating RP2040- and
RP2350-family examples and example-backed targets.

## Scope

This policy applies to Raspberry Pi RP2-family MCU work in AEL, including:

- RP2040
- RP2350
- future closely related RP2-family devices

It specializes the general DUT target generation policy for RP2-family work.

## Purpose

For RP2-family work, AEL should prefer local validated AEL references as the
main structural baseline.

For the first RP2350 path in a new line, AEL should combine:

- official Pico SDK support for the board/platform
- the closest local validated RP2040 AEL target shape

The goal is to:

- keep build and flash behavior aligned with Pico SDK support
- preserve local AEL runtime/test structure where already validated
- avoid unnecessary divergence across RP2-family targets

## Preferred source order

### RP2040

Use source material in this order:

1. closest locally validated AEL RP2040 target/example
2. official Pico SDK board/example support when needed to fill device facts
3. provisional minimal fallback only when no suitable local reference exists

### RP2350

Use source material in this order:

1. official Pico SDK board/platform support for the first RP2350 target
2. closest locally validated AEL RP2040 or RP2350 target shape for structure
3. once one RP2350 target is validated locally, prefer local RP2350 reference
   first for later RP2350 expansion

## Required separation of concerns

Generated RP2-family examples must keep these concerns distinct:

- Pico SDK / official board support facts
  - `PICO_BOARD`
  - `PICO_PLATFORM`
  - startup/runtime support
  - target-specific build support
- AEL-owned example behavior
  - GPIO signature logic
  - timing and verify-friendly waveform shape
  - board/test integration choices
- board-specific bench assumptions
  - observed GPIO pins
  - control-instrument choice
  - wiring assumptions

## Generation rules

When generating a new RP2-family example:

1. choose the closest local AEL RP2-family reference first
2. for a first RP2350 path, anchor platform/board selection to official Pico
   SDK support
3. keep the Pico SDK build structure intact
4. adapt only the AEL-owned behavior and board assumptions needed for the new
   board
5. keep artifact naming and project paths explicit in board config

## Provenance requirements

RP2-family generated targets should record:

- official Pico SDK board/platform basis when used
- local AEL reference target used
- which files are structurally copied or adapted
- which files remain AEL-owned
- whether runtime validation has occurred

## Validation requirements

Generated RP2-family examples must be validated conservatively and in stages:

1. static path/naming consistency
2. `inventory describe-test`
3. `explain-stage --stage plan`
4. build-stage confirmation
5. `pre-flight`, `run`, and `check` only when bench conditions are ready

Do not claim runtime validation from generation alone.

## Current policy summary

- RP2040 future work: local-reference-first
- first RP2350 path: official Pico SDK support plus local RP2040 AEL target
  shape
- later RP2350 work: local-reference-first once a validated RP2350 baseline
  exists

## Relationship to other docs

- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
- [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)
