# STM32F411CEU6 official-source case study

This file is a case-study example, not the primary rule document.

Primary rules now live in:
- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
- [stm32_official_source_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32_official_source_generation_policy_v0_1.md)
- [stm32_generation_catalog_v0_1.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32_generation_catalog_v0_1.json)

## Why this target matters

`stm32f411ceu6` is the first STM32 target in AEL rebuilt from official ST
source support rather than from a purely provisional template-derived target.

## Source basis used

- fetched ST STM32Cube source with:
  - `tools/fetch_stm32cubef4.sh`
- source cache:
  - `third_party/cache/STM32CubeF4`
- copied official device support into:
  - `firmware/targets/stm32f411ceu6/vendor/`

Copied ST source classes:
- GCC startup file
- family system file
- STM32F411 device headers
- memory-template basis for the linker script

## AEL-owned vs copied files

Copied ST files:
- `vendor/st/startup_stm32f411xe.s`
- `vendor/st/system_stm32f4xx.c`
- `vendor/include/st/stm32f4xx.h`
- `vendor/include/st/stm32f411xe.h`
- `vendor/include/st/system_stm32f4xx.h`

AEL-owned files:
- `main.c`
- `Makefile`
- `stm32f411.ld`
- `provenance.md`

## What this case study proves

- the STM32Cube cache workflow is sufficient for target-local vendor extraction
- an AEL target can use official STM32 startup/system/CMSIS support without
  adopting ST board BSP assumptions
- provenance can be recorded locally in a way that keeps the cache itself
  gitignored

## Validation completed

- target build passed
- AEL plan stage passed for:
  - `inventory describe-test`
  - `inventory describe-connection`
  - `explain-stage --stage plan`

## Remaining caveats

- board-level GPIO and LED mapping remain provisional
- no hardware flash/verify result has been claimed yet
- `PC13` dual observation mapping is still a known bench assumption to review
