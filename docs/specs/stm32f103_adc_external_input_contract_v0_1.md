# STM32F103 ADC External Input Contract v0.1

## Purpose

Define the first concrete external-input contract for a generated ADC example
without requiring immediate live execution.

Target:

- `stm32f103_adc_banner`

## Contract

The execution contract for the first bounded STM32 ADC path is:

- source: `FIXED_3V3_SUPPLY`
- DUT signal: `PA0/ADC1_IN0`
- kind: `analog_in`
- expected range: `2.8V .. 3.45V`

## Meaning

This contract is now explicit and formal.

It does **not** mean the path is runtime-ready immediately.
It means:

- connection questions can be answered formally
- the analog source is no longer unspecified
- the remaining blocker is bench provisioning, not missing contract definition

## Current Remaining Blocker

The current blocker is:

- `blocked_missing_bench_setup`

That is narrower than the earlier:

- `blocked_unbound_external_input`

## Why This Is The Right First ADC Step

This removes one real blocker without requiring:

- UART setup work
- broad ADC execution rollout
- broader bench redesign

It is a bounded first execution-enablement step.
