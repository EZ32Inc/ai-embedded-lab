# ST-Link Alignment Review

Date: 2026-03-18
Status: Batch 6A/6B/6C Review

## Scope

This note records the first deeper ST-Link alignment pass against the
`esp32_jtag` reference backend.

Reference side:

- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)

Aligned side:

- [ael/instruments/backends/stlink.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink.py)
- [ael/instruments/backends/stlink_backend/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/backend.py)

## Batch 6A: Error Normalization

Applied:

- typed ST-Link backend exceptions in
  [errors.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/errors.py)
- `error_code_for(...)` mapping for direct backend failures

Effect:

- direct backend execution now emits structured failures with explicit codes such as:
  - `invalid_request`
  - `connection_timeout`
  - `program_failed`
  - `target_not_halted`
  - `verify_failed`

## Batch 6B: Package Split

Applied:

- created ST-Link backend package:
  - [backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/backend.py)
  - [transport.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/transport.py)
  - [capability.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/capability.py)
  - [actions/flash.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/actions/flash.py)
  - [actions/reset.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/actions/reset.py)
  - [actions/debug_halt.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/actions/debug_halt.py)
  - [actions/debug_read_memory.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/actions/debug_read_memory.py)
- kept [stlink.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink.py) as a compatibility shim

Effect:

- ST-Link now has roughly the same package boundary shape as `esp32_jtag`
- dispatcher import path remains stable

## Batch 6C: Cross-Backend Contract Review

What is now aligned:

- explicit backend wrapper class
- explicit capability declaration
- explicit action handler map
- structured direct backend result shape
- legacy-edge bridge back into IAM `ok/error_code/message` shape

What still drifts:

- ST-Link action handlers still receive `instrument` directly rather than a persistent transport object
- `esp32_jtag` transport supports compat/native modes; ST-Link uses only GDB batch helper flow
- ST-Link does not yet expose a dedicated request/response transport abstraction comparable to `Esp32JtagTransport`
- error taxonomy names are closer now but not fully shared across backends

Decision:

- current alignment is sufficient for a first controlled migration pass
- do not force a fake shared transport abstraction yet
- keep the next pass focused on reusable GDB-remote helpers only if another backend needs them
