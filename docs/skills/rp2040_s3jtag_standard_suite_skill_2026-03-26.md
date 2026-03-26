# RP2040 S3JTAG Standard Suite Skill

## Purpose

Capture the reusable pattern for building a no-extra-wire `standard` validation suite on `S3JTAG` for `RP2040`, extending the earlier smoke-only `1 kHz` signal check into a broader set of digital outcomes.

## When To Use

Use this skill when:
- the control instrument is `S3JTAG` backed by a generic `ESP32-S3 devkit`
- SWD flashing already works
- the only validated observe path is a single `TARGETIN` GPIO
- you want the richest useful suite before adding UART, SPI, ADC, or reset wiring

## Validated Standard Pack

Formal pack:
- `packs/standard_rp2040_s3jtag.json`

Validated tests:
- `rp2040_minimal_runtime_mailbox_s3jtag`
- `rp2040_gpio_level_low_with_s3jtag`
- `rp2040_gpio_level_high_with_s3jtag`
- `rp2040_gpio_signature_100hz_with_s3jtag`
- `rp2040_gpio_signature_with_s3jtag`

Validated run ids on 2026-03-26:
- `2026-03-26_07-44-49_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag`
- `2026-03-26_07-44-59_rp2040_pico_s3jtag_rp2040_gpio_level_low_with_s3jtag`
- `2026-03-26_07-45-18_rp2040_pico_s3jtag_rp2040_gpio_level_high_with_s3jtag`
- `2026-03-26_07-45-49_rp2040_pico_s3jtag_rp2040_gpio_signature_100hz_with_s3jtag`
- `2026-03-26_07-46-20_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag`

## Bench Contract

Required wiring:
- `GPIO4` -> target `SWCLK`
- `GPIO5` -> target `SWDIO`
- `GPIO15 TARGETIN` <- target `GPIO16`
- common `GND`

Explicitly not required for this skill:
- UART wiring
- SPI wiring
- ADC wiring
- target reset line

## Reusable Rule

When the instrument only has `SWD + one digital input`, the best next suite is:
1. mailbox runtime proof
2. steady `low` proof
3. steady `high` proof
4. slower toggle proof
5. faster toggle proof

Do not skip directly from smoke to UART/SPI expansion if these basic digital states are still unproven.

## Important Implementation Rule

`TARGETIN` verification must not treat `toggle` as the only valid success state.

The test plan should be able to declare:
- `expected_state: low`
- `expected_state: high`
- `expected_state: toggle`

And the runtime should evaluate the returned `state` accordingly.

## Recovery / Interpretation Notes

If the first live sample after flashing looks wrong:
- do not immediately conclude the bench is broken
- check whether the sample landed in the target startup window
- use the final persisted `verify_result.json` for the run outcome

Validated final outcome shapes:
- low: `state=low transitions=0 estimated_hz=0`
- high: `state=high transitions=0 estimated_hz=0`
- 100 Hz: `state=toggle estimated_hz=99`
- 1 kHz: `state=toggle estimated_hz=999`

## Why This Skill Matters

This turns `S3JTAG` from a one-off smoke path into a reusable digital-standard instrument class:
- it can prove that code runs
- it can prove static target output levels
- it can prove low-rate and high-rate toggles
- it can do all of that without extra bench wiring

That is the right stable foundation before UART work starts.
