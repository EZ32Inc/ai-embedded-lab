# STM32F103 Density Exactness Skill 2026-03-28

## Purpose

Capture the reusable rule for STM32F103 bring-up when the MCU density changes
but an existing F103 path looks superficially similar.

## Scope

Use this when:

- the user presents a new STM32F103 board
- the exact part number is not the same as the closest existing repo target
- the existing candidate target uses a different flash/RAM density
- the bring-up would otherwise be tempted to reuse the generic STM32F103 path
  unchanged

## Core Rule

Do not reuse an STM32F103 target purely by family name. Check exact device
density first.

For `STM32F103C6T6`, do not blindly reuse a `C8`-sized or larger memory map.
Confirm:

- flash size
- RAM size
- startup stack top

If they do not match, add an exact wrapper or exact target before flashing.

## Why

In this session, the closest existing path was a Bluepill-like STM32F103
mailbox/self-check target. It was structurally reusable, but its memory map was
not exact for `STM32F103C6T6`.

The existing generic path assumed:

- `64 KB` flash
- `20 KB` RAM
- stack top `0x20005000`

The exact `STM32F103C6T6` path required:

- `32 KB` flash
- `10 KB` RAM
- stack top `0x20002800`

The image was small, but relying on the larger map would still be an incorrect
bring-up assumption.

## Recommended Workflow

1. Identify the exact MCU from user-provided evidence.
2. Summarize setup and get confirmation before execution.
3. Find the closest existing board/test methodology path.
4. Separate methodology reuse from device-memory assumptions.
5. If density differs, create an exact wrapper target or exact linker/startup.
6. Then run the first live flash.

## Bench Note

For the validated ESP32JTAG BMDA path on this board, the working flash sequence
used:

- `monitor swdp_scan`
- `attach`
- `load`
- second `attach`
- `detach`

## Current Known Conclusion

For STM32F103 bring-up, exact MCU identification is not enough by itself.
Density-specific linker and startup assumptions must also match the exact part
before first flash.
