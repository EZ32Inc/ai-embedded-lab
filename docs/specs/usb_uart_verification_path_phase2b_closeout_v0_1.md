# USB-to-UART Verification Path Phase 2b Closeout v0.1

## Scope

This note closes Phase 2b of the bounded USB-to-UART verification-path work.

Phase 2b scope was:

- same board
- same test
- same UART success marker
- same control instrument
- remote bridge daemon/service on another host

## Concrete Path

- board: `stm32f103`
- test: `stm32f103_uart_banner`
- success marker:
  - `AEL_READY STM32F103 UART`

Instrument roles:

- control instrument:
  - `esp32jtag_stm32_golden @ 192.168.2.99:4242`
- UART instrument:
  - `usb_uart_bridge_daemon @ 192.168.2.78:8767`

## Remote Host Role

The remote host acted only as a USB-to-UART instrument node/service running the
bridge daemon.

It did not act as:

- a second orchestrator
- a remote worker
- a cloud/session node

## Strongest Runtime Evidence

The strongest runtime proof that the bounded UART verification path used the
remote bridge endpoint is:

- run:
  - `runs/2026-03-12_17-44-00_stm32f103_stm32f103_uart_banner/`
- artifact:
  - `runs/2026-03-12_17-44-00_stm32f103_stm32f103_uart_banner/uart_observe.json`

That artifact records:

- `bridge_endpoint = 192.168.2.78:8767`
- `ok = true`
- matched expected marker:
  - `AEL_READY STM32F103 UART`

## What Phase 2b Proves

Phase 2b proves that:

- the same bounded STM32 UART verification path still works when the bridge
  daemon runs on another host
- AEL can use the remote `IP:port` instead of the local endpoint
- the bridge remains a network-addressable instrument service rather than a
  local serial shortcut

## What Phase 2b Does Not Prove

Phase 2b does not prove:

- general multi-instrument runtime support
- broad remote AEL worker/orchestrator design
- cloud registration/session infrastructure
- broad UART framework behavior

## Acceptance Criteria Assessment

1. the USB-to-UART bridge daemon runs on a different host
   - satisfied
2. AEL uses the remote endpoint instead of the local endpoint
   - satisfied
3. the same bounded STM32 UART verification path passes on real hardware
   - satisfied
4. the same success marker is observed through the remote bridge
   - satisfied
5. the result is documented as a bounded remote-host proof only
   - satisfied

## Result

Phase 2b is complete.
