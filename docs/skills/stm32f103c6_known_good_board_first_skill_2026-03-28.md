# STM32F103C6 Known-Good Board First Skill 2026-03-28

## Purpose

Capture the reusable rule for bring-up on low-cost Bluepill-like
`STM32F103C6T6` boards when multiple nominally identical units are available.

## Scope

Use this when:

- the board type is Bluepill-like or clone-like
- the MCU is `STM32F103C6T6`
- visible LED behavior is part of first bring-up
- more than one physical board of the same claimed type exists
- some units behave inconsistently

## Core Rule

Do not spend too long debugging a complex firmware image on an uncertain board.

First establish:

- one minimal known-good firmware
- one known-good physical board

Then use that pair as the baseline before diagnosing the other boards.

## Minimal Baseline For This Case

For this session, the accepted baseline was:

- minimal `PC13`-only blinky
- `BSRR` set/reset writes
- active-low LED behavior
- no mailbox logic
- no unrelated GPIO activity

## Why

The earlier firmware path was more complex than needed for LED diagnosis, and
multiple same-type boards did not behave the same way.

That means two failure classes were mixed together:

- firmware diagnostic ambiguity
- physical board variation or fault

The fix was to reduce firmware to a reference-style blinky and validate it on a
different same-type board. That immediately separated the two.

## Recommended Workflow

1. Identify the exact MCU and summarize setup.
2. Use the smallest possible LED-only firmware first.
3. Flash one board and check visible behavior.
4. If behavior is ambiguous, try another same-type board before escalating
   firmware complexity.
5. Once one board works, freeze that firmware as the known-good baseline.
6. Treat later failures on other same-type boards as possible hardware issues,
   not automatic firmware regressions.

## Current Known Conclusion

For Bluepill-like `STM32F103C6T6` bring-up, a known-good board plus a minimal
reference-style `PC13` blinky is the right first anchor. That prevents firmware
and hardware uncertainty from being mixed together.
