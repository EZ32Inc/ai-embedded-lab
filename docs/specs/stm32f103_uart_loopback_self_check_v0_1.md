# STM32F103 UART Loopback Self-Check v0.1

## Purpose
Add the missing unified-board UART self-check path on the primary `stm32f103` capability anchor without using the external USB-UART bridge path.

## Fixture
- Board: `stm32f103`
- Control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- Preserved unified fixture wiring:
  - `PA4 -> P0.0` (main external proof line)
  - `PA9 -> PA10` (UART internal loopback)

## UART roles
- `PA9 = USART1_TX`
- `PA10 = USART1_RX`

## Method
- Firmware transmits bounded alternating bytes on `USART1_TX`
- RX loopback on `PA10` must receive the same byte
- Firmware exports loopback-valid status onto `PA4`
- AEL verifies `PA4` through the normal STM32 observe path

## Success method
- `PA4` shows the expected machine-checkable waveform only when UART loopback is valid
- Failures should collapse `PA4` low or otherwise break the expected waveform

## Regression framing
- Change class: `Class 3`
- Affected anchor: `stm32f103` primary sample-board capability anchor
- Minimum regression tier: `Tier 4`

## Validation commands
```bash
python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/stm32f103_uart_loopback_banner.json
python3 -m ael explain-stage --board stm32f103 --test tests/plans/stm32f103_uart_loopback_banner.json --stage plan
python3 -m ael run --board stm32f103 --test tests/plans/stm32f103_uart_loopback_banner.json
```
