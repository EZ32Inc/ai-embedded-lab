# STM32F401 BMDA Second-Attach Skill 2026-03-28

## Purpose

Capture the reusable debug rule for STM32F401 boards flashed through ESP32JTAG
BMDA when firmware loads successfully but the target does not appear to keep
running immediately after flash.

## Scope

Use this when all of the following are true:
- board family is `STM32F401`
- flash path is ESP32JTAG BMDA over GDB remote
- `load` succeeds
- user-visible behavior suggests the target is not really running after flash
- power cycle or unplug/replug makes the firmware start behaving correctly

## High-Signal Symptom Pattern

- SWD attach works
- firmware downloads successfully
- AEL may reach run stage, but visible board behavior is wrong or missing
- after target repower, the flashed image behaves correctly

This symptom pattern means "image was loaded" is not enough. The post-load GDB
session semantics must be checked.

## Working Rule

For the validated STM32F401 BMDA path, keep the historical sequence:

- `file {firmware}`
- `monitor a`
- `attach {target_id}`
- `load`
- `attach {target_id}`
- `detach`

Do not replace this blindly with:
- `monitor reset run`

## Why

In this session, replacing the historical second attach with `monitor reset run`
caused a regression in post-flash behavior. Restoring the second attach matched
repo history and restored immediate LED blink on hardware.

Relevant historical repo evidence:
- STM32 BMDA stabilization commit added the second attach to
  `stm32f401rct6`
- the same attach pattern appears in the older STM32F4 bench model

## Diagnosis Workflow

1. Confirm the board facts first.
   - exact MCU
   - whether LED is onboard and which pin drives it
   - whether only SWD is connected
2. Confirm SWD health.
   - target visible over BMDA
   - flash `load` succeeds
3. Separate "flash finished" from "target is visibly running".
   - use operator-visible LED behavior if that is the intended outcome
4. Check board-family repo history before changing post-load GDB commands.
5. If STM32F401 BMDA had a known second-attach sequence, restore that first.

## Anti-Pattern To Avoid

- assuming a generic `monitor reset run` fix is safer than the bench-specific
  sequence already validated for this board family

## Session Evidence

- board: `STM32F401RCT6`
- LED: `PC13`
- bench: ESP32JTAG at `192.168.2.106`
- confirmed good run after restore:
  - `2026-03-28_18-51-23_stm32f401rct6_stm32f401_led_blink`

## Current Known Conclusion

For STM32F401 boards on this ESP32JTAG BMDA path, prefer the historical
second-attach post-load sequence over `monitor reset run` unless new live
evidence proves otherwise.
