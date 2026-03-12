# USB-to-UART Verification Path Phase 2a Closeout v0.1

## Scope

This note closes Phase 2a of the bounded USB-to-UART verification-path work.

Phase 2a scope was:

- same host
- separately started bridge daemon/service
- explicit endpoint-based bridge use
- same bounded STM32 UART verification contract as Phase 1

## Concrete Path

- board: `stm32f103`
- test: `stm32f103_uart_banner`
- success marker:
  - `AEL_READY STM32F103 UART`

Instrument roles:

- control instrument:
  - `esp32jtag_stm32_golden @ 192.168.2.99:4242`
- UART instrument:
  - `usb_uart_bridge_daemon @ 127.0.0.1:8767`

## Strongest Runtime Evidence

The strongest runtime proof for Phase 2a is the real live pass where the bridge
daemon was started separately and the UART verification artifact recorded the
bridge endpoint:

- run:
  - `runs/2026-03-12_16-17-00_stm32f103_stm32f103_uart_banner/`
- artifact:
  - `runs/2026-03-12_16-17-00_stm32f103_stm32f103_uart_banner/uart_observe.json`

That artifact shows:

- `bridge_endpoint = 127.0.0.1:8767`
- `ok = true`
- matched expected marker:
  - `AEL_READY STM32F103 UART`

## What Phase 2a Proves

Phase 2a proves that:

- the USB-to-UART bridge can run as a separate local daemon/service
- AEL can use it explicitly by endpoint as a network-addressable instrument
- the bounded STM32 UART verification path still passes with real hardware

## What Phase 2a Does Not Prove

Phase 2a does not prove:

- remote-host use
- general multi-instrument runtime support
- broad UART framework support
- cloud/distributed-lab orchestration

## Acceptance Criteria Assessment

1. the USB-to-UART bridge daemon can be started separately on the same host
   - satisfied
2. AEL uses the bridge by explicit endpoint in the STM32 UART path
   - satisfied
3. the bounded STM32 UART verification path passes with real hardware
   - satisfied
4. at least one real live pass exists with the bridge daemon running as a
   separate service process
   - satisfied

## Result

Phase 2a is complete.

## Smallest Correct Starting Point for Phase 2b

Keep the same:

- board
- test
- success marker
- control instrument
- UART verify contract

Change only:

- the UART instrument endpoint from `127.0.0.1:8767` to a different host's
  `IP:port`

The remote host should still act only as an instrument node/service, not as a
second orchestrator.
