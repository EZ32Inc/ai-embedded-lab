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
- current status: validated on real hardware and used in current default verification, but bench-side meter/Wi-Fi instability is still intermittent

What is currently solid in this path:

- golden firmware builds as `esp32c6`
- flash to the attached board is working
- UART readiness token validation is working
- meter-based digital GPIO signature verification is working
- analog rail verification is working
- standardized validation summary and last-known-good setup output are present
- `current_setup` now captures current bench-side setup facts for this path

Known nuance:

- current failures in this path are best interpreted as degraded instrument / degraded bench behavior unless new evidence points elsewhere
- recent failures have included:
  - meter unreachable
  - meter API/transport timeout
  - late `instrument.signature` timeout after DUT UART readiness was already confirmed

### 2. RP2040 / Raspberry Pi Pico Verification Path

- board family: `rp2040`
- validation style: control-instrument-backed pre-flight + build + BMDA/GDB flash + logic-analyzer verify
- main control-instrument path: `esp32jtag_rp2040_lab` at `192.168.2.63:4242` with LA verify via `https://192.168.2.63:443`
- current status: validated on real hardware and stable in current default verification

What is currently solid in this path:

- pre-flight control-instrument/network/LA checks are working
- build and flash are working
- logic-analyzer verification is working
- standardized validation summary and last-known-good setup output are present

Known nuance:

- RP2040 flash may emit BMDA/GDB remote failure warnings after load, but the path is currently treated as healthy when downstream verify passes

### 3. STM32F103 / Bluepill Verification Path

- board family: `stm32f103`
- validation style: control-instrument-backed pre-flight + build + BMDA/GDB flash + logic-analyzer verify
- main control-instrument path: `esp32jtag_stm32_golden` at `192.168.2.98:4242` with LA verify via `https://192.168.2.98:443`
- current status: validated on real hardware and stable in current default verification

What is currently solid in this path:

- pre-flight control-instrument/network/LA checks are working
- build and flash are working
- logic-analyzer verification is working
- the STM32 BMDA post-load reattach sequence is stable in repeated golden runs
- standardized validation summary and last-known-good setup output are present

## Current Default Verification Set

Current default verification sequence:

1. `esp32c6_golden_gpio`
2. `rp2040_golden_gpio_signature`
3. `stm32f103_golden_gpio_signature`

Source:

- [default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)

Current status:

- default verification is functioning correctly across all three configured paths, but the ESP32-C6 worker can still fail intermittently because of bench-side meter instability

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
- communication metadata is now carried through configs, summaries, archive output, and inventory views
- capability-to-surface metadata is now available as metadata for instrument and probe paths

What is still only partially formed:

- instrument backend dispatch is still partly concrete-backend-oriented
- broader instrument abstraction is clarified architecturally, but only partially aligned in code
- capability-to-surface metadata is informational only and is not yet used for runtime routing
- degraded-instrument recovery remains intentionally bounded; classification/reporting is ahead of recovery automation

## Current Stable Strengths

The most important strengths that are now clearly real:

- multiple MCU families are validated in practice
- multiple bench interaction styles are already working:
  - Wi-Fi instrument path
  - control-instrument/JTAG/logic-analyzer path
- default verification covers more than one family and more than one validation style
- evidence-driven validation is real, not hypothetical
- successful runs now produce usable summaries instead of only raw logs
- current known-good hardware paths are being preserved while structure is improved incrementally

## Current Known Gaps Or Incomplete Areas

Important incomplete areas remain.

Most relevant current gaps:

- not all paths expose the same level of setup clarity
- instrument abstraction is improved, but not yet fully unified in implementation
- some intermittent meter-side timeout behavior has been observed in reruns
- the workflow/skills layer is growing, but still not broad enough to cover all recurring review patterns
- some older docs/examples still use legacy probe-first wording and remain candidates for gradual cleanup

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

### 1. Continue Small Compatibility / Contract Cleanup

Examples:

- keep shrinking visible legacy compatibility wording
- tighten active bench/resource and DUT/runtime output contracts where operator value is clear

### 2. Stabilize Occasional Meter Timeout Behavior

Examples:

- continue observing transient `check_meter` timeout cases
- improve evidence only if remaining ambiguity still costs time in practice

### 3. Keep Validating Current Known-Good Paths

Examples:

- continue running default verification regularly
- treat RP2040 and STM32F103 as stable baseline confidence paths, with ESP32-C6 as both a validated path and a useful degraded-instrument stress case

## Summary

At this stage, AEL is a working real-hardware validation system with:

- multiple validated board families
- multiple validated bench interaction styles
- a default verification system whose orchestration is working correctly even when one instrument path is degraded
- clearer board/test/instrument/bench boundaries than before
- a workflow that is now structured enough to support careful next-step cleanup without losing the current known-good paths
