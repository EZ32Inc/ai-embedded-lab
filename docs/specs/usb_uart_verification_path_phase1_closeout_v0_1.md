# USB-to-UART Verification Path Phase 1 Closeout v0.1

## Scope

This note closes Phase 1 of the bounded local USB-to-UART verification-path
work.

Phase 1 scope was:

- local USB-to-UART instrument use only
- one concrete board target
- one bounded UART success contract
- one real live end-to-end pass

This phase was intentionally not:

- general multi-instrument runtime support
- remote-host USB-to-UART support
- broad UART framework work

## Concrete Board/Test Used

- board: `stm32f103`
- test: `stm32f103_uart_banner`

## Concrete Success Contract

Bounded UART success marker:

- `AEL_READY STM32F103 UART`

Pass criteria for this path were limited to observing that expected UART marker
through the USB-to-UART instrument path while the existing control instrument
handled flash/control duties.

## Instrument Roles Used

This was a bounded local 2-instrument execution path:

- control instrument:
  - `esp32jtag_stm32_golden @ 192.168.2.99:4242`
- UART instrument:
  - `usb_uart_bridge_daemon @ 127.0.0.1:8767`

The control instrument remained responsible for flash/load and existing
GPIO-side verification support.

The USB-to-UART bridge was used for UART observe verification.

## Strongest Runtime Evidence

The strongest runtime proof that UART verification used the bridge path rather
than bypassing it is:

- run:
  - `runs/2026-03-12_16-17-00_stm32f103_stm32f103_uart_banner/`
- UART observe artifact:
  - `runs/2026-03-12_16-17-00_stm32f103_stm32f103_uart_banner/uart_observe.json`

That artifact records:

- `bridge_endpoint = 127.0.0.1:8767`
- `ok = true`
- matched expected marker:
  - `AEL_READY STM32F103 UART`

This is stronger evidence than a plan-only contract because it shows the
runtime UART verify result came back through the bridge path in a real pass.

## What Phase 1 Proves

Phase 1 proves that:

- the USB-to-UART instrument can run locally
- AEL can start/use it in local mode
- AEL can use it as a real verification instrument on one concrete board path
- a bounded UART success contract can be executed end-to-end with real hardware
- the resulting execution path can pass in real use

## What Phase 1 Does Not Prove

Phase 1 does not prove:

- general multi-instrument runtime support
- arbitrary 3-instrument or N-instrument orchestration
- remote-host USB-to-UART execution
- broad UART console framework support
- broad generated-example runtime enablement

This is still only a bounded local USB-to-UART verification path.

## Acceptance Criteria Assessment

Phase 1 acceptance criteria:

1. the USB-to-UART instrument can run locally
   - satisfied
2. it can be started/used by AEL in local mode
   - satisfied
3. it can work with one concrete board target, preferably STM32F103
   - satisfied (`stm32f103`)
4. one bounded UART success contract is defined
   - satisfied (`AEL_READY STM32F103 UART`)
5. AEL can execute that verification path end-to-end with real hardware
   - satisfied
6. at least one real live run passes
   - satisfied

## Phase 1 Result

Phase 1 is complete.

## Out of Scope

Still out of scope after Phase 1:

- general multi-instrument runtime support
- remote-host execution
- broad serial framework work
- adding this path directly into a broader baseline set without a separate
  decision

## Smallest Correct Starting Point for Phase 2

Phase 2 should start from the same bounded verification contract and the same
board/test path.

The smallest correct Phase 2 starting point is:

- run the same `stm32f103_uart_banner` path
- keep the same success marker
- move only the USB-to-UART bridge daemon to a different host
- make AEL use that remote bridge endpoint instead of the local endpoint

No broader runtime redesign is required to start Phase 2.
