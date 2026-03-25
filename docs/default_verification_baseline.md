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

The current baseline is one nine-worker parallel batch defined in
[configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml).

### Required (6)

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

- DUT: `stm32f103_gpio_stlink`
- DUT test: `stm32f103_gpio_no_external_capture_stlink`
- Plan: `tests/plans/stm32f103_gpio_no_external_capture_stlink.json`

### Optional candidates (3)

These run in parallel with the required batch but do not affect the PASS/FAIL
result. They skip gracefully when hardware is not on bench.

- DUT: `stm32f407_discovery` *(optional — onboard ST-Link, hardware-gated)*
- DUT test: `stm32f407_mailbox`
- Plan: `tests/plans/stm32f407_mailbox.json`

- DUT: `stm32f401rct6` *(optional — ESP32JTAG, hardware-gated)*
- DUT test: `stm32f401_gpio_signature`
- Plan: `tests/plans/stm32f401_gpio_signature.json`

- DUT: `esp32_wroom32d_cp210x` *(optional — CP210x, hardware-gated; 6 jumpers required)*
- DUT test: `esp32_wroom32d_test_full_suite`
- Plan: `tests/plans/esp32_wroom32d/test_full_suite.json`
- Note: bench-validated 2026-03-25; 12/12 PASS (`AEL_SUITE_FULL DONE passed=12 failed=0`)

## Current validated result

This baseline is no longer only a configured suite. It has repeated live-bench
validation as a parallel regression line.

Representative evidence:

- first full six-way parallel pass: `2026-03-20_10-33-07`
- three consecutive repeated passes: `2026-03-20_10-36-49`, `10-37-43`, `10-38-37`
- ST-Link USB freeze fixed (SIGKILL + USBDEVFS_RESET ioctl); 3/3 consecutive passes confirmed `2026-03-21`
- ST-Link promoted from optional to required; suite confirmed `6/6 PASS` on `2026-03-21`
- Optional candidates (F407 Discovery, F401RCT6) added; suite confirmed `PASS (6/8)` on `2026-03-21`
- ESP32-WROOM-32D bench-validated (12/12 PASS); added as optional candidate `2026-03-25`

A regression on `2026-03-20` temporarily broke all four `ESP32JTAG`-backed runs
at preflight (lost provider-resolution metadata after interface standardization);
repaired and baseline returned to `6/6 PASS` in run `2026-03-20_13-10-38`.

## Current baseline meaning

At the current project stage, this baseline should be treated as:

- the default regression health line for schema and execution-model changes
- the main repeated live-bench stability line for the current nine-board setup (6 required + 3 optional)
- the primary readiness signal before expanding to broader mixed-instrument
  coverage

## Notes

- Default verification does not define its own test names anymore.
- Default verification does not define a second setup for the same test.
- If setup changes are needed, update the DUT test plan, not the default verification config.
- Repeated reliability collection should prefer worker-level repeat commands when the goal is long-horizon stability measurement.
