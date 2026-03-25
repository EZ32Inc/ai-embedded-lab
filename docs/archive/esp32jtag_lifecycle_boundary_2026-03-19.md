# ESP32JTAG Lifecycle Boundary Note

Date: 2026-03-19

## Purpose

Record the intended lifecycle boundary for `ESP32JTAG` as an instrument-level
API so future work does not mix metadata/health surfaces with backend action
execution.

## In Scope For `jtag_native_api`

- identity
- capability-family reporting
- status
- doctor
- preflight
- runtime presentation support for instrument view/doctor surfaces

## Still Owned By `esp32_jtag` Backend

- flash
- reset
- debug halt
- debug memory read
- gpio measure
- transport details

## Explicitly Out Of Scope For Now

- provision
- service restart
- device firmware update
- session orchestration
- moving existing backend execution actions into instrument API

## Reason

`ESP32JTAG` is a multi-capability instrument, but that does not mean every
operation belongs in the instrument API layer.

The instrument API should explain:

- what the instrument is
- what subsystems it has
- whether those subsystems are healthy

The backend should execute test actions.

Keeping this split explicit avoids turning `jtag_native_api` into a second
action backend.
