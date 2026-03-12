# Default Verification 4-Worker Health Note 2026-03-12

## Purpose

Record the first bounded repeat-health result for the 4-worker default-verification suite.

## Command

```bash
python3 -m ael verify-default repeat --limit 3
```

## Result

- `rp2040_golden_gpio_signature`: `3/3 PASS`
- `stm32f103_golden_gpio_signature`: `3/3 PASS`
- `stm32f103_uart_bridge_banner`: `3/3 PASS`
- `esp32c6_golden_gpio`: `1/2 PASS`, then stopped on iteration 2

## Observed failure

The only failure in this bounded repeat run was:

- worker: `esp32c6_golden_gpio`
- iteration: `2`
- error: `timed out`

This matches the known ESP32-C6 meter-side instability pattern and does not indicate a new regression in the added STM32 UART bridge worker.

## Main conclusions

1. The two STM32 workers are now correctly separated by DUT identity.
2. The STM32 UART bridge worker remained healthy across all attempted iterations.
3. The two STM32 workers still serialize on the shared control instrument, which is expected.
4. The only instability observed in the repeat run remained the known ESP32-C6 meter-backed path.

## Strongest bounded evidence

- `stm32f103_golden_gpio_signature`: `3/3 PASS`
- `stm32f103_uart_bridge_banner`: `3/3 PASS`
- remote UART bridge endpoint remained in use for the UART worker:
  - `192.168.2.78:8767`

## Scope boundary

This note is a bounded health record only.

It does not claim that the full 4-worker suite is free of bench-side instability, because the ESP32-C6 meter path remains known to be intermittent.

