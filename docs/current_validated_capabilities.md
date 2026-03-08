# Current Validated Capabilities

## Purpose

This document captures the current validated state of AEL after the recent real-hardware validation work.

It is an internal engineering baseline.

Its purpose is to record:

- what is currently known to work well
- what is now reasonably standardized
- what is only partially formed
- what boundaries and next steps matter most right now

## Current Validated Board/Test Paths

### 1. ESP32-C6 Golden GPIO / Meter Path

- board family: `esp32c6`
- validation style: DUT firmware build + flash + UART readiness + external meter-based digital/analog verification
- main instrument path: `esp32s3_dev_c_meter` over `192.168.4.1:9000`
- current status: validated on real hardware and used in current default verification

What is currently solid in this path:

- golden firmware builds as `esp32c6`
- flash to the attached board is working
- UART readiness token validation is working
- meter-based digital GPIO signature verification is working
- analog rail verification is working
- standardized validation summary and last-known-good setup output are present
- `current_setup` now captures current bench-side setup facts for this path

### 2. RP2040 / Raspberry Pi Pico Verification Path

- board family: `rp2040`
- validation style: probe-based pre-flight + build + BMDA/GDB flash + logic-analyzer verify
- main probe path: `ESP32JTAG` at `192.168.2.63:4242` with LA verify via `https://192.168.2.63:443`
- current status: validated on real hardware and stable in current default verification

What is currently solid in this path:

- pre-flight probe/network/LA checks are working
- build and flash are working
- logic-analyzer verification is working
- standardized validation summary and last-known-good setup output are present

Known nuance:

- RP2040 flash may emit BMDA/GDB remote failure warnings after load, but the path is currently treated as healthy when downstream verify passes

## Current Default Verification Set

Current default verification sequence:

1. `esp32c6_golden_gpio`
2. `rp2040_golden_gpio_signature`

Source:

- [default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)

Current status:

- default verification is passing across both paths on real hardware

## Current Workflow Maturity

The workflow is now in reasonably good shape in several important areas.

Current stronger areas:

- new-board bring-up flow has been clarified in a dedicated document
- `plan`-stage readiness summary expectations are explicit
- validation summary output is standardized
- last-known-good setup output is standardized
- stage semantics now distinguish executed, skipped, and deferred
- meter-based bench mapping has moved toward explicit `bench_setup`
- current setup facts have started to be grouped explicitly in `current_setup`

This does not mean the workflow is fully mature.

It does mean AEL now has a usable, repeatable validation flow rather than a collection of only ad hoc successful runs.

## Current Instrument Architecture Status

Instrument architecture is now clearer than before, though still incomplete.

What has been clarified:

- instrument is treated as a bench-side capability layer
- board / test / instrument / bench setup boundaries are more explicit
- the ESP32-S3 meter path is now understood as a concrete instrument-capability example
- meter DUT-to-instrument mapping is now represented as `bench_setup` in active meter-based test plans
- current selected setup facts are beginning to be grouped as run-time setup facts

What is still only partially formed:

- probe/JTAG paths do not yet expose setup/session facts as explicitly as the meter path
- instrument backend dispatch is still partly concrete-backend-oriented
- broader instrument abstraction is clarified architecturally, but only partially aligned in code

## Current Stable Strengths

The most important strengths that are now clearly real:

- multiple MCU families are validated in practice
- multiple bench interaction styles are already working:
  - Wi-Fi instrument path
  - probe/JTAG/logic-analyzer path
- default verification covers more than one family and more than one validation style
- evidence-driven validation is real, not hypothetical
- successful runs now produce usable summaries instead of only raw logs
- current known-good hardware paths are being preserved while structure is improved incrementally

## Current Known Gaps Or Incomplete Areas

Important incomplete areas remain.

Most relevant current gaps:

- probe/JTAG path still lacks richer `current_setup` style grouping
- not all paths expose the same level of setup clarity
- instrument abstraction is improved, but not yet fully unified in implementation
- some intermittent meter-side timeout behavior has been observed in reruns
- skills remain important, but they are not yet the main stabilized system layer
- existing docs such as `docs/default_verification.md` still reflect older ESP32-S3 defaults and need cleanup

## Current Product / Engineering Decisions

These decisions appear to be true right now:

- do not rush into many more new boards immediately
- preserve the currently working ESP32-C6 and RP2040 paths while improving structure
- prefer small, architecture-aligned cleanups over broad refactors
- instrument work is now foundational and should continue carefully
- skills remain important, but they should build on clearer boundaries
- validated hardware paths should remain the anchor for future design decisions

## Suggested Near-Term Next-Step Options

These are realistic near-term options, not a large roadmap.

### 1. Continue Small Instrument-Side Cleanup

Examples:

- improve probe-path current setup grouping
- clarify selected setup facts in more non-meter paths

### 2. Stabilize Occasional Meter Timeout Behavior

Examples:

- investigate transient `check_meter` timeout cases
- improve diagnostics around meter-side timeout failures without redesigning the flow

### 3. Keep Validating Current Known-Good Paths

Examples:

- continue running default verification regularly
- treat ESP32-C6 + RP2040 as the current baseline confidence set

## Summary

At this stage, AEL is a working real-hardware validation system with:

- at least two validated board families
- multiple validated bench interaction styles
- passing default verification across those validated paths
- clearer board/test/instrument/bench boundaries than before
- a workflow that is now structured enough to support careful next-step cleanup without losing the current known-good paths
