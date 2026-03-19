# ESP32JTAG Instrument API Runtime Surface Closeout

Date: 2026-03-19

## Scope

This closeout records the follow-on batch that moved `ESP32JTAG` from a
"minimal native API exists" state to a clearer runtime-facing instrument API.

Completed scope:

- align runtime presentation with `instrument_family = esp32jtag`
- expand status/doctor into subsystem-oriented health domains
- document lifecycle boundary explicitly
- collect more healthy live doctor samples
- align default-verification runtime labeling with `jtag_native_api`

Out of scope:

- moving action execution into `jtag_native_api`
- provision/restart lifecycle implementation
- replacing every remaining generic control path in one batch

## What Changed

Implementation:

- [ael/instruments/jtag_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/jtag_native_api.py)
- [ael/instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)
- [ael/instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)

New docs:

- [docs/esp32jtag_instrument_api_completeness_checklist_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_instrument_api_completeness_checklist_2026-03-19.md)
- [docs/esp32jtag_lifecycle_boundary_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_lifecycle_boundary_2026-03-19.md)
- [docs/esp32jtag_optional_lifecycle_surface_review_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_optional_lifecycle_surface_review_2026-03-19.md)

## Runtime Result

`ESP32JTAG` now presents a clearer instrument-level model in runtime surfaces:

- runtime family: `esp32jtag`
- owned native actions:
  - `preflight_probe`
- native metadata/status/doctor domains:
  - `network`
  - `gdb_remote`
  - `web_api`
  - `capture_subsystem`
  - `monitor_targets`

`default_verification` now labels `ESP32JTAG`-backed steps as:

- `jtag_native_api`

instead of the older generic:

- `control_instrument_native_api`

## Healthy Live Samples

Healthy doctor samples now exist for:

- `esp32jtag_stm32f411 @ 192.168.2.103`
- `esp32jtag_g431_bench @ 192.168.2.62`
- `esp32jtag_rp2040_lab @ 192.168.2.63`
- `esp32jtag_h750_bench @ 192.168.2.106`

This means the runtime-facing instrument API evidence now spans multiple target
families and bench configurations.

## Phase Decision

This batch was enough to make the runtime identity more truthful.

The next phase should stay narrow:

- continue using `esp32_jtag` backend for execution
- only expand instrument-level lifecycle surfaces when there is a real runtime
  need
- prefer more evidence and small runtime clarifications over broad refactors
