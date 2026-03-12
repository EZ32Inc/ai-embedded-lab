# USB-to-UART Verification Path Phase 2a Plan v0.1

## Scope

Phase 2a validates the USB-to-UART bridge as a separately started instrument
service on the same host.

This phase is intentionally bounded:

- same host only
- same board/test/success marker as Phase 1
- same control-instrument role
- no broad UART framework work
- no remote-host work yet
- no general multi-instrument runtime work

## Objective

Prove that AEL uses the USB-to-UART bridge explicitly as a network-addressable
instrument endpoint, even when the bridge daemon runs on the same host.

In other words, Phase 2a validates deployment shape, not a new verification
contract.

## Invariants from Phase 1

Keep these unchanged:

- board: `stm32f103`
- test: `stm32f103_uart_banner`
- success marker: `AEL_READY STM32F103 UART`
- control instrument:
  - `esp32jtag_stm32_golden @ 192.168.2.99:4242`
- UART instrument id:
  - `usb_uart_bridge_daemon`
- required UART wiring:
  - `PA9/USART1_TX -> USB-UART RX`
  - `GND -> USB-UART GND`

## What Changes in Phase 2a

Only this changes from the architectural point of view:

- the bridge must be treated explicitly as a separately started daemon/service
- AEL must use the configured `host:port` bridge endpoint
- the runtime path must not fall back to a direct local serial access shortcut
  for the bounded STM32 UART verification flow

## Acceptance Criteria

Phase 2a is complete when all of the following are true:

1. the USB-to-UART bridge daemon can be started separately on the same host
2. AEL uses the bridge by explicit endpoint in the STM32 UART path
3. the bounded STM32 UART verification path passes with real hardware
4. at least one real live pass exists with the bridge daemon running as a
   separate service process

## Regression Rule

If any shared runtime surface is changed while validating Phase 2a, run:

```bash
python3 -m ael verify-default run
```

## Non-Goals

Phase 2a does not include:

- moving the bridge daemon to another host
- cloud registration/session work
- general multi-instrument runtime support
- general UART console framework work
- generated-example expansion work
