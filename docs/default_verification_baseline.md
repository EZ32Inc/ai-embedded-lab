# Default Verification Baseline

Default verification now selects DUT tests only. The DUT test plan remains the single source of truth for:

- test identity
- bench setup and connections
- control instrument selection
- expected checks

## Current configured steps

- DUT: `esp32c6_devkit`
- DUT test: `esp32c6_gpio_signature_with_meter`
- Plan: `tests/plans/esp32c6_gpio_signature_with_meter.json`

- DUT: `rp2040_pico`
- DUT test: `rp2040_gpio_signature`
- Plan: `tests/plans/rp2040_gpio_signature.json`

- DUT: `stm32f103_gpio`
- DUT test: `stm32f103_gpio_signature`
- Plan: `tests/plans/stm32f103_gpio_signature.json`

- DUT: `stm32f103_uart`
- DUT test: `stm32f103_uart_banner`
- Plan: `tests/plans/stm32f103_uart_banner.json`

## Current validated result

- default verification run:
  - `2026-03-13_19-43-04_esp32c6_devkit_esp32c6_gpio_signature_with_meter` -> `PASS`
  - `2026-03-13_19-44-57_stm32f103_gpio_stm32f103_gpio_signature` -> `PASS`
  - `2026-03-13_19-45-37_stm32f103_uart_stm32f103_uart_banner` -> `PASS`
- current non-code blocker:
  - `rp2040_gpio_signature` is presently blocked by RP2040 probe/Wi-Fi reachability on `192.168.2.63`

## Notes

- Default verification does not define its own test names anymore.
- Default verification does not define a second setup for the same test.
- If setup changes are needed, update the DUT test plan, not the default verification config.
