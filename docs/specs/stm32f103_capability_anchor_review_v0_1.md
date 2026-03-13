# STM32F103 Capability Anchor Review v0.1

## Purpose
- record the current bounded STM32F103 capability-anchor state
- preserve what is already real-pass on the unified fixture
- stop further demo expansion by momentum

## Current anchor role
- `stm32f103` is the primary sample-board capability anchor

## Preserved paths
- GPIO golden baseline on the normal STM32 golden setup
- UART bridge path on the separate `stm32f103_uart` board and remote bridge path

## Unified self-check paths now real-pass
- ADC closed-loop
- UART loopback
- SPI self-check
- PWM self-check
- GPIO loopback self-check
- EXTI self-check
- capture/timing self-check

## Unified fixture summary
- control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- main external proof line: `PA4 -> P0.0`
- optional auxiliary observe: `PA5 -> P0.1`
- preserved loopbacks:
  - `PA1 -> PA0`
  - `PA9 -> PA10`
  - `PA7 -> PA6`
  - `PA8 -> PB8`

## What this anchor now proves
- AEL can support multiple bounded generated execution proofs on one reused STM32 fixture with minimal rewiring
- the STM32 anchor is strong enough to serve as the primary sample-board capability baseline

## What this anchor does not prove
- broad multi-board capability equivalence
- external-path protocol verification beyond the bounded proofs already implemented
- I2C readiness

## Stop boundary
- do not add another STM32 capability demo by default
- any next STM32 path should be chosen intentionally from a fresh direction decision
