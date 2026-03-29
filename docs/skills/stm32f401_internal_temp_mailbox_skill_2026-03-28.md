# Skill: Use ADC1 Channel 18 For STM32F401 Internal Temperature Stage 1

## Trigger

Use this when:
- adding a no-wire internal peripheral self-test for STM32F401
- the desired proof is internal temperature sensing without external analog wiring

## Implementation Pattern

For STM32F401:
- enable `ADC1`
- set `ADC_CCR.TSVREFE`
- select regular channel `18`
- use a long sample time for channel 18
- run multiple conversions
- report result through mailbox

## Proven Shape

Validated on `STM32F401RCT6`:
- firmware:
  - `firmware/targets/stm32f401rct6_internal_temp_mailbox/`
- test:
  - `tests/plans/stm32f401rct6_internal_temp_mailbox.json`

PASS rule used:
- sample 8 times
- average must be non-zero
- average must not be saturated
- spread must be non-zero

Mailbox reporting:
- `detail0 = (spread << 16) | average`

## Reusable Lesson

For an early Stage 1 STM32F401 internal sensor test:
- prefer mailbox over UART
- avoid absolute temperature calibration requirements
- use bounded plausibility checks instead of Celsius conversion first
- keep the proof focused on internal ADC + sensor path health
