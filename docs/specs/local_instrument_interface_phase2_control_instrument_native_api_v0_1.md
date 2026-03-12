# Local Instrument Interface Phase 2 Control Instrument Native API v0.1

## Purpose

This note defines the minimum control-instrument native API needed for Phase 2
default-verification migration.

It is intentionally limited to:

- `rp2040_golden_gpio_signature`
- `stm32f103_golden_gpio_signature`

## Required Metadata Commands

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

## Required Verification-Time Actions

- `capture_signature`
- `observe_gpio`

These are sufficient for the current signal-verification step.

## Explicitly Deferred

The following are not part of this Phase 2 native API unless they become
strictly required by the default-verification paths:

- broad flash/debug migration
- universal reset/debug command coverage
- broad control-instrument family unification

## Practical Phase 2 Rule

For RP2040 and STM32 default verification, the verification-time capture path
should use this native API, while orchestration-level flash/debug behavior
remains outside the lower layer for now.
