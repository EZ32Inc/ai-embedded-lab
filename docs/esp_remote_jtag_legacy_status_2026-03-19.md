# ESP Remote JTAG Legacy Status

Date: 2026-03-19

## Decision

`esp_remote_jtag` is now explicitly treated as a legacy compatibility driver.

It remains runnable for older configs, but it no longer owns an independent
mixed implementation.

## Current Behavior

The legacy driver now forwards to current reference backends:

- `flash` -> `esp32_jtag`
- `reset` -> `esp32_jtag`
- `gpio_measure` -> `esp32_jtag`
- `voltage_read` -> `esp32_meter`

Implementation:

- [ael/instruments/backends/esp_remote_jtag.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp_remote_jtag.py)

## Why

Before this change, `esp_remote_jtag` still mixed:

- remote JTAG flashing/debug behavior
- meter-backed digital measurement
- meter-backed voltage reads

That shape overlapped with the newer package-style backends and risked further
behavior drift.

## Boundary

This was intentionally not a full deletion batch.

The old driver name still works for compatibility, but it is no longer a place
to add new logic. New action/backend work should land in:

- `esp32_jtag`
- `esp32_meter`

## Practical Rule

If an existing config still uses `driver: esp_remote_jtag`, it should be treated
as a legacy path and migrated only when there is a concrete reason.
