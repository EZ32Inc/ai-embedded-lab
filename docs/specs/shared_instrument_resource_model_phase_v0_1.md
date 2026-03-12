# Shared Instrument Resource Model Phase v0.1

## Purpose

This phase defines the minimum correct shared-instrument/resource model needed
to remove unnecessary blocking caused by overly coarse ownership modeling,
while preserving blocking where the resource is truly shared.

This is a bounded design/contract phase first.

It does not start broad runtime concurrency implementation.

## Concrete phase goal

Using current real default-verification behavior as evidence, define the
minimum resource model needed so AEL can correctly distinguish:

- resources that are truly shared and must block
- resources that are currently collapsed together incorrectly
- resources that could be independent if modeled at finer granularity

## Concrete success condition

At the end of this phase, AEL should have a clear, bounded answer to:

1. what current blocking is correct
2. what current blocking is too coarse
3. what minimum new abstraction would be required to remove unnecessary
   blocking safely
4. whether one tiny implementation experiment is justified now

## Current motivating baseline

The main motivating execution evidence is the current 4-worker default suite:

1. `rp2040_golden_gpio_signature`
2. `stm32f103_golden_gpio_signature`
3. `stm32f103_uart_bridge_banner`
4. `esp32c6_golden_gpio`

The most concrete shared-resource case in that baseline is:

- `stm32f103_golden_gpio_signature`
- `stm32f103_uart_bridge_banner`

These two workers:

- now use separate DUT identities
- still serialize on the same `esp32jtag_stm32_golden` control instrument

## Scope boundary

This phase is intentionally limited to:

- current resource model clarification
- future abstraction definition
- one concrete pilot analysis using `esp32jtag_stm32_golden`
- one bounded decision on whether a tiny experiment is justified

This phase does not include:

- broad runtime concurrency implementation
- general multi-instrument support
- broad control-instrument redesign
- generated-example work
- broad bench or multi-board redesign

## Non-goals

This phase does not claim:

- that AEL already supports shareable sub-resource concurrency
- that the current STM32 shared-control-instrument case should be relaxed now
- that every future instrument family needs immediate channel-level ownership

## Deliverables

1. current model vs future model mapping
2. minimum future abstraction
3. concrete `esp32jtag_stm32_golden` pilot analysis
4. stop/go decision on any tiny implementation experiment

## Stop boundary

This phase is complete when:

- the current model gap is written clearly
- the minimum future abstraction is defined
- the pilot case is analyzed concretely
- there is a bounded decision on whether to stop at design or try one tiny
  implementation experiment

If the pilot does not reveal a clearly safe, clearly useful tiny change, the
correct result is to stop at design.

