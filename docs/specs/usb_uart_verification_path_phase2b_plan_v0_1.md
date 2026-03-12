# USB-to-UART Verification Path Phase 2b Plan v0.1

## Scope

Phase 2b validates the same bounded STM32 UART verification path when the
USB-to-UART bridge daemon runs on a different host.

This phase is intentionally bounded:

- same board
- same test
- same UART success marker
- same control instrument
- only the UART bridge endpoint moves to a remote host

## Objective

Prove that AEL can use the USB-to-UART bridge daemon as a remote
network-addressable instrument service without changing the bounded verification
contract.

## Required Invariants

Keep these unchanged from Phase 1 / Phase 2a:

- board: `stm32f103`
- test: `stm32f103_uart_banner`
- success marker:
  - `AEL_READY STM32F103 UART`
- control instrument:
  - `esp32jtag_stm32_golden @ 192.168.2.99:4242`
- required UART wiring:
  - `PA9/USART1_TX -> USB-UART RX`
  - `GND -> USB-UART GND`

## What Changes

Only this changes:

- the UART bridge daemon runs on a different host
- AEL uses the remote endpoint:
  - `192.168.2.78:8767`

## Recommended Remote Host Role

The remote host should run only the USB-to-UART bridge daemon/service.

It should not act as:

- a full remote AEL orchestrator
- a remote worker/scheduler
- a cloud/session node

## Acceptance Criteria

Phase 2b is complete when all of the following are true:

1. the USB-to-UART bridge daemon runs on a different host
2. AEL uses the remote endpoint instead of the local endpoint
3. the same bounded STM32 UART verification path passes on real hardware
4. the same success marker is observed through the remote bridge
5. the result is recorded as a bounded remote-host proof only

## Non-Goals

Phase 2b does not include:

- general multi-instrument runtime support
- broad UART framework work
- cloud registration/session infrastructure
- remote orchestrator/worker design
