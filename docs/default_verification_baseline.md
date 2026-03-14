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

- DUT: `stm32f411ceu6`
- DUT test: `stm32f411_gpio_signature`
- Plan: `tests/plans/stm32f411_gpio_signature.json`

## Current validated result

- latest live default-verification run with the current five-step config:
  - `esp32c6_gpio_signature_with_meter` -> `FAIL`
    - reason: flash stage reported `no serial port found`
  - `2026-03-14_09-27-35_rp2040_pico_rp2040_gpio_signature` -> `PASS`
  - `2026-03-14_09-27-58_stm32f103_gpio_stm32f103_gpio_signature` -> `PASS`
  - `2026-03-14_09-28-28_stm32f103_uart_stm32f103_uart_banner` -> `PASS`
  - `2026-03-14_09-29-06_stm32f411ceu6_stm32f411_gpio_signature` -> `PASS`
- current non-code nuance:
  - the baseline configuration is valid, but the ESP32-C6 path can still fail when its flash serial path is unavailable

## Notes

- Default verification does not define its own test names anymore.
- Default verification does not define a second setup for the same test.
- If setup changes are needed, update the DUT test plan, not the default verification config.
