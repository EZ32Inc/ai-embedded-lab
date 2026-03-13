# Capability Expansion Skill v0.1

## Purpose
- support the design and generation of the next bounded capability demo on a current anchor board
- keep capability expansion tied to real fixture reuse, machine-checkable success criteria, and bounded regression scope

## Scope
- one board anchor at a time
- one capability path at a time
- one bounded success contract at a time
- one regression framing decision at a time

This skill is intended for:
- choosing the next bounded capability demo
- validating pin/peripheral/fixture correctness
- deciding the machine-checkable observe path
- defining the minimum repo artifacts to generate

This skill is not intended for:
- multi-family expansion
- broad framework design
- broad multi-instrument runtime work
- broad hardware redesign

## Inputs
- current anchor board/setup
- current proven and preserved paths
- proposed next capability
- board pin/peripheral constraints
- current fixture wiring
- current regression-tier rules

## Outputs
- bounded next-capability decision
- corrected pin/wiring proposal
- bounded success criteria
- machine-checkable observe path
- change class / affected anchor / minimum regression tier
- repo artifact plan

## Decision Rules
- prefer reuse of the current stable anchor fixture
- preserve already-proven paths unless there is a strong reason to change them
- prefer one blocker, one path, one proof
- prefer one unified external observe path when practical
- keep external instruments and wiring minimal
- reject paths that introduce broad setup cost without strong execution value
- distinguish clearly between:
  - self-check demo
  - future external-path demo

## Stop Points
Stop and do not broaden if:
- the next path requires a new family setup
- the success criteria are not machine-checkable
- pinmux/peripheral correctness is uncertain
- the path requires broad runtime/framework changes
- the path requires broad new hardware setup rather than a small fixture delta

## Repo Interaction
This skill should produce or update only the minimum useful artifact set, typically:
- one fixture/setup note
- one per-demo spec
- one test/plan definition
- one validation command list
- one regression framing note

## How It Applies To Current STM32F103 Work
Current STM32F103 anchor facts:
- preserved ADC closed-loop path:
  - `PA1 -> PA0`
  - ADC result encoded onto `PA4`
- immediate next bounded path:
  - SPI self-check
  - `PA5 = SPI1_SCK`
  - `PA7 = SPI1_MOSI`
  - `PA6 = SPI1_MISO`
  - `PA7 -> PA6`
  - `PA4` remains the external machine-checkable output
- second-wave path:
  - `PA8 -> PB8`
- I2C remains reserved/exploratory

For this STM32F103 anchor, this skill should currently prefer:
- the SPI self-check path as the next bounded capability expansion step
- reuse of the current STM32F103 fixture and PA4 observe path
