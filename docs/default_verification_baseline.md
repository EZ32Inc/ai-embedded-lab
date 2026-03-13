# Default Verification Baseline

Default verification now selects DUT tests only. The DUT test plan remains the single source of truth for:

- test identity
- bench setup and connections
- control instrument selection
- expected checks

## Current configured step

- DUT: `stm32f103`
- DUT test: `stm32f103_gpio_signature`
- Plan: `tests/plans/stm32f103_gpio_signature.json`

## Current validated result

- default verification run:
  - run id: `2026-03-13_18-22-08_stm32f103_stm32f103_gpio_signature`
  - result: `PASS`

## Notes

- Default verification does not define its own test names anymore.
- Default verification does not define a second setup for the same test.
- If setup changes are needed, update the DUT test plan, not the default verification config.
