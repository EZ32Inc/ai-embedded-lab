# Default Verification 4-Worker Baseline v0.1

## Purpose

Record the current bounded default-verification suite shape after adding the STM32 UART bridge path.

## Current workers

The default-verification suite currently includes:

1. `rp2040_golden_gpio_signature`
2. `stm32f103_golden_gpio_signature`
3. `stm32f103_uart_bridge_banner`
4. `esp32c6_golden_gpio`

## STM32 split

The two STM32 workers are intentionally modeled as different DUTs:

- `stm32f103_golden_gpio_signature` uses DUT identity `stm32f103`
- `stm32f103_uart_bridge_banner` uses DUT identity `stm32f103_uart`

This means they are no longer treated as the same physical board.

## Shared control instrument

The two STM32 workers still share the same control instrument:

- `esp32jtag_stm32_golden`
- endpoint `192.168.2.99:4242`

Under the current instrument-instance ownership model, this means:

- they do not serialize on DUT identity
- they do serialize on the shared control-instrument resource

This is the expected bounded behavior today.

## UART worker shape

`stm32f103_uart_bridge_banner` is a bounded 2-instrument execution path:

- control instrument:
  - `esp32jtag_stm32_golden`
- UART instrument:
  - `usb_uart_bridge_daemon`

The UART verification success marker is:

- `AEL_READY STM32F103 UART`

## Scope boundary

This note records the current default-verification baseline only.

It does not claim:

- general multi-instrument runtime support
- shared sub-resource support inside one instrument
- broad UART framework support

