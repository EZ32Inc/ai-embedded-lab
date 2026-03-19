# Skill: ESP32JTAG Runtime Surface Alignment

## When To Use

Use this when `ESP32JTAG` already has a backend and a minimal native API, but
runtime-facing surfaces still describe it too generically.

Typical signal:

- execution works
- doctor/view work
- but runtime labels still say `control_instrument_native_api` or otherwise
  flatten `ESP32JTAG` into a generic control probe

## Goal

Align runtime naming and health reporting with the actual instrument model,
without moving action execution out of the backend.

## Steps

1. Check runtime presentation surfaces.
- inspect `instrument_view`
- inspect `instrument_doctor`
- inspect CLI output
- inspect health summaries like `default_verification`

2. Keep backend ownership stable.
- do not move `flash/reset/debug/gpio_measure` into the instrument API just to
  make labels cleaner

3. Expand health domains only where they clarify real subsystems.
- `network`
- `gdb_remote`
- `web_api`
- `capture_subsystem`
- `monitor_targets`

4. Prefer explicit family naming.
- use `instrument_family = esp32jtag`
- use `jtag_native_api` where the runtime path is really entering the JTAG
  instrument-level interface

5. Validate with real doctor samples.
- do not rely only on unit tests
- collect healthy samples from multiple benches if possible

## Important Boundary

This skill is about runtime truthfulness, not backend migration.

Keep:

- identity/status/doctor/preflight in `jtag_native_api`
- execution in `esp32_jtag backend`

## What Good Looks Like

- runtime text/json surfaces clearly say `esp32jtag`
- health reports are subsystem-oriented
- default/runtime summaries no longer mislabel the path as generic when it is
  specifically `jtag_native_api`
