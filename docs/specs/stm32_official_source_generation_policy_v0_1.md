# STM32 Official-Source Generation Policy v0.1

This document defines the STM32-specific rules for official-source-based AEL
target generation.

## Scope

This policy applies when an STM32 target is generated or refreshed from official
ST sources such as STM32Cube and CMSIS device support.

It does not replace the general DUT target generation policy. It specializes it
for STM32.

## Official source selection order

Use official ST source in this order:

1. CMSIS device headers for the exact device line
2. official startup file for the exact device line and toolchain
3. official `system_*.c` for the family line
4. official linker or memory template for the device line
5. family/device examples only as structural references

Do not use BSP board examples as the source of AEL board assumptions such as LED
pin choice or probe wiring.

## Required source classes

For an official-source-based STM32 target, the following should come from ST:

- startup file
- system file
- device/family headers needed by the target
- memory template basis for the linker script

The following remain AEL-owned:

- `main.c`
- `Makefile`
- target-local linker script
- `provenance.md`
- board config and bench assumptions

## Target-local vendor layout

Official STM32 targets should keep copied vendor material inside the target
directory under `vendor/`.

Expected layout:

- `vendor/st/`
  - copied startup file
  - copied system file
- `vendor/include/st/`
  - copied STM32 headers needed by the target

This keeps copied files clearly separated from AEL-generated files and avoids
confusing target-local material with the source cache.

## Source cache workflow

The repo-local source cache is a fetch/update helper, not committed source of
truth.

For STM32CubeF4, use:

- `tools/fetch_stm32cubef4.sh`
- cache location:
  - `third_party/cache/STM32CubeF4`

The cache itself is intentionally gitignored. The committed target must carry
the exact provenance needed to reconstruct the copied subset.

## Low-level generation constraints

When official STM32 headers provide definitions, do not hand-define:

- raw peripheral base addresses
- register offsets
- core register layouts already present in CMSIS

Allowed AEL low-level code:

- direct register access using official CMSIS types and macros
- minimal runtime glue such as a trivial `__libc_init_array()` when justified by
  the selected startup file and bare-metal build model

## Linker script rules

The linker script may be AEL-owned, but its memory sizes and address ranges must
be derived from official ST device templates or CMSIS/device documentation.

The linker script should make it obvious which values came from the official
template basis.

## Provenance requirements

Target-local `provenance.md` must include:

- official source repo
- exact revision or tag
- copied file paths
- target-local destination paths
- AEL-generated files
- local AEL glue or deviations

## Validation requirements

An official-source-based STM32 target is not complete until it has at least:

1. build pass
2. AEL plan-stage validation pass

If runtime or hardware validation has not been performed, that target must stay
in a non-runtime-verified status in the STM32 generation catalog.
