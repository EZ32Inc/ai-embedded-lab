# AEL Next-Phase Direction Memo

Date: 2026-03-19
Status: Internal planning memo
Source: extracted from `/nvme1t/work/codex/ali_everyday_notes/road_map_chatgpt_discussion_2026-03-19.txt`

## Purpose

This memo consolidates the project-direction discussion from the shared chat and
turns it into a repo-facing planning document.

The goal is to identify:

- the immediate next-phase priorities
- the supporting infrastructure that should be built alongside them
- the documentation/spec work that is still needed

## Current Project State

AEL has already demonstrated:

- end-to-end AI-driven embedded workflow
  - firmware generation
  - compilation
  - flashing
  - execution
  - validation
  - iterative debugging
- multi-platform validation
  - STM32
  - ESP32
  - RP2040
- real hardware execution with meaningful results

The project is moving from:

- "AI can do embedded tasks"

to:

- "AI performs structured embedded engineering"

## Priority Overview

### Primary Focus

#### 1. AEL Pattern Library

Why:

- converts ad-hoc AI behavior into repeatable engineering methods
- enables stability, reuse, and scalability
- is the foundation for RTOS, QA, and expansion work

Scope for v1:

- bring-up patterns
- debug patterns
- validation patterns
- instrument usage patterns
- initial RTOS patterns

Immediate actions:

- define pattern schema
- define pattern directory structure
- implement initial core patterns:
  - `gpio_signature`
  - `uart_banner`
  - `wiring_mismatch`
  - `repeated_run_consistency`

Key principle:

- patterns are executable engineering knowledge, not just documentation

#### 2. Test Versioning System

Why:

- tests will evolve over time
- existing validated tests must remain stable
- reproducibility and regression depend on stable contracts

Core rules:

- tests are versioned contracts
- old versions are immutable
- new behavior requires a new version

Immediate actions:

- introduce versioned test structure
- support explicit version selection
- store selected version in run metadata

Key principle:

- a test is a contract, not just code

### Secondary Focus

#### 3. ESP32 Expansion

Why:

- ESP-IDF gives relatively unified coverage across chip families
- high visible value for comparatively low effort
- useful proof of scalable AEL support

Target families discussed:

- ESP32-S3
- ESP32-C6
- ESP32-C5
- ESP8266 if practical

Constraint:

- expansion should be pattern-driven, not manual duplication

#### 4. RP2040 Formalization

Goal:

- raise RP2040 support to the same operational level as STM32 and ESP32

Required consistency:

- patterns
- tests
- validation

### Controlled Advancement

#### 5. RTOS / Embedded OS Support

Importance:

- pushes AEL from bare-metal validation toward system-level engineering
- better represents real product scenarios

Strategy:

- do not jump directly into complex systems
- build this on top of pattern + versioning first

Near-term RTOS ladder:

- Phase A: minimal RTOS patterns
  - single task
  - dual task
  - queue
  - semaphore
- Phase B: RTOS-aware validation
- Phase C: driver + RTOS integration

Key principle:

- RTOS amplifies complexity and should be introduced through a minimal,
  pattern-first path

## Supporting Infrastructure

These items should be considered early even if they are not the first
implementation target.

### 1. Support Tier / Maturity Levels

Needed maturity levels:

- experimental
- prototype
- working
- validated
- golden

Why:

- prevents over-trusting unstable components
- gives the AI a clearer reliability signal

### 2. Capability Matrix

The discussion calls for an explicit mapping of:

- board -> supported instruments
- instrument -> capabilities
- test -> required capabilities
- pattern -> compatible environments

Why:

- combination count grows quickly across MCU, board, instrument, and test

### 3. Board Reality Layer

The project should separate:

- logical board definition
  - MCU
  - default config
- physical instance description
  - wiring
  - instrument
  - power
  - notes

Why:

- real bench setup drifts from abstract board definitions

### 4. Run Artifact Contract

Each run should preserve:

- plan or prompt summary
- firmware version
- board and instrument metadata
- test plus version
- pattern used
- logs
- structured result
- evidence such as waveform or UART capture

Why:

- results alone are not enough for replay, QA, or learning

### 5. Failure Taxonomy

The chat proposes an initial planning taxonomy:

- `build_failure`
- `flash_failure`
- `transport_failure`
- `observation_failure`
- `expectation_mismatch`
- `wiring_suspected`
- `board_definition_suspected`
- `instrument_capability_gap`
- `environment_suspected`

Why:

- enables reusable debug strategies
- aligns strongly with pattern-driven recovery

### 6. Migration Strategy

Rules:

- do not break existing tests
- wrap instead of rewrite
- new features follow the new structure
- legacy remains runnable

## Golden Baseline Strategy

The project should maintain a small set of:

- highly stable
- repeatedly validated
- trusted configurations

Purpose:

- debugging reference
- regression baseline
- system sanity check

## Target Selection Policy

When choosing what to expand next, use:

- popularity
- SDK consistency
- bring-up cost
- reuse potential
- instrument compatibility
- maintenance cost

## Execution Split

The extracted recommendation from the chat is:

- 70% Pattern Library
- 20% Test Versioning
- 10% ESP32 and RP2040 expansion

RTOS:

- design patterns now
- delay broad implementation

Constraint:

- do not perform large-scale refactors
- build incrementally on top of the current working system

## Documentation Actions

This section translates the memo into concrete repo doc work.

### New Docs That Still Need To Be Added

- `docs/ael_pattern_library_v1.md`
- `docs/ael_test_versioning_v0_1.md`
- `docs/rtos_validation_ladder_v0_1.md`
- `docs/capability_matrix_v0_1.md`
- `docs/support_tier_maturity_model_v0_1.md`
- `docs/board_reality_layer_v0_1.md`
- `docs/run_artifact_contract_v0_1.md`
- `docs/golden_baseline_strategy_v0_1.md`
- `docs/target_selection_policy_v0_1.md`

### Existing Docs With Partial Overlap

- [docs/failure_taxonomy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/failure_taxonomy_v0_1.md)
  - already covers part of the needed failure taxonomy, but should eventually
    align terminology with planning-level categories and recovery usage
- [docs/role_first_migration_pattern.md](/nvme1t/work/codex/ai-embedded-lab/docs/role_first_migration_pattern.md)
  - useful migration guidance, but not a replacement for the broader Pattern
    Library spec
- [docs/instrument_manifest_v0.1.md](/nvme1t/work/codex/ai-embedded-lab/docs/instrument_manifest_v0.1.md)
  - contributes to the future capability matrix and board/instrument mapping
- [docs/dut_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/dut_model.md)
  - relevant to the logical side of the board reality split
- [docs/default_verification.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification.md)
  - relevant to golden baseline and repeatable QA

## Summary

The chat points to one main conclusion:

- the next phase should prioritize structure over feature count

Immediate priorities:

- Pattern Library
- Test Versioning

Parallel but bounded work:

- ESP32 expansion
- RP2040 formalization

Controlled next-step capability:

- RTOS support, introduced through minimal patterns first

The supporting infrastructure that should not be missed:

- maturity levels
- capability matrix
- board reality layer
- run artifact contract
- failure taxonomy alignment
- migration rules
