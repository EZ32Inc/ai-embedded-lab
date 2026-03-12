# Shared Instrument Resource Model Phase Closeout v0.1

## Result

This bounded phase should stop at design.

## Why design-only is enough for now

The current 4-worker default baseline exposed one real bounded modeling issue:

- false DUT-level collapse between the two STM32 workers

That issue has already been fixed by splitting:

- `stm32f103`
- `stm32f103_uart`

After that fix, the remaining STM32 blocking is at the shared control
instrument level.

For the current active STM32 paths, the evidence does not yet justify
relaxing that blocking.

## Concrete phase outcome

This phase clarified:

- what current blocking is correct
- what current blocking was too coarse
- what minimum future abstraction would be needed for finer-grained sharing

The minimum future abstraction would need:

- instrument instance
- capability
- sub-resource / channel
- access mode
- ownership policy

## Tiny implementation experiment decision

Decision: **not justified now**

Reason:

- the current pilot does not identify a clearly safe, clearly useful,
  bounded runtime relaxation
- one mistaken experiment could weaken the now-stable default baseline

## What this phase proves

1. current AEL ownership is still whole-instrument oriented
2. false resource collapsing can be identified and fixed at the correct layer
3. the remaining shared control-instrument blocking in the active STM32 pilot
   is still the correct safe behavior

## What this phase does not prove

- that ESP32JTAG sub-resource sharing is safe
- that current same-instrument blocking should be reduced now
- that AEL is ready for general channel-level concurrency

## Recommended next step

Do not continue this track into implementation by momentum.

Only reopen shared-instrument runtime work if a future execution case provides:

- a concrete same-instrument path
- clearly disjoint sub-resources
- and a clearly safe, bounded runtime experiment

