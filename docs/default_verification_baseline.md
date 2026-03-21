# Default Verification Baseline

Default verification is now the system-owned regression baseline for the current
repo-native hardware line.

It selects DUT tests only. The DUT test plan remains the single source of truth
for:

- test identity
- bench setup and connections
- control instrument selection
- expected checks

## Current configured steps

The current baseline is one six-worker parallel batch defined in
[configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml).

- DUT: `esp32c6_devkit`
- DUT test: `esp32c6_gpio_signature_with_meter`
- Plan: `tests/plans/esp32c6_gpio_signature_with_meter.json`

- DUT: `rp2040_pico`
- DUT test: `rp2040_gpio_signature`
- Plan: `tests/plans/rp2040_gpio_signature.json`

- DUT: `stm32f411ceu6`
- DUT test: `stm32f411_gpio_signature`
- Plan: `tests/plans/stm32f411_gpio_signature.json`

- DUT: `stm32g431cbu6`
- DUT test: `stm32g431_gpio_signature`
- Plan: `tests/plans/stm32g431_gpio_signature.json`

- DUT: `stm32h750vbt6`
- DUT test: `stm32h750_wiring_verify`
- Plan: `tests/plans/stm32h750_wiring_verify.json`

- DUT: `stm32f103_gpio_stlink` *(optional — pending hardware validation)*
- DUT test: `stm32f103_gpio_no_external_capture_stlink`
- Plan: `tests/plans/stm32f103_gpio_no_external_capture_stlink.json`

## Current validated result

This baseline is no longer only a configured suite. It has repeated live-bench
validation as a parallel regression line.

Representative evidence:

- first full six-way parallel pass:
  - `2026-03-20_10-33-07`
- three consecutive repeated six-way parallel passes:
  - `2026-03-20_10-36-49`
  - `2026-03-20_10-37-43`
  - `2026-03-20_10-38-37`

Each run set passed all six experiments, including the previously unstable
local ST-Link path `stm32f103_gpio_no_external_capture_stlink`.

A later regression on `2026-03-20` temporarily broke all four `ESP32JTAG`-backed
default-verification runs at preflight time. The benches were healthy; the
run-time `probe_cfg` had lost provider-resolution metadata after interface
standardization. That regression was repaired, and the baseline again returned
to `6/6 PASS` in run set `2026-03-20_13-10-38`.

## Current baseline meaning

At the current project stage, this baseline should be treated as:

- the default regression health line for schema and execution-model changes
- the main repeated live-bench stability line for the current six-board setup
- the primary readiness signal before expanding to broader mixed-instrument
  coverage

## Notes

- Default verification does not define its own test names anymore.
- Default verification does not define a second setup for the same test.
- If setup changes are needed, update the DUT test plan, not the default verification config.
- Repeated reliability collection should prefer worker-level repeat commands when the goal is long-horizon stability measurement.
