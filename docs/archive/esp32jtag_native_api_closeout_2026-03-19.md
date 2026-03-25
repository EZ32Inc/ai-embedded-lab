# ESP32JTAG Native API Minimal Integration Closeout

Date: 2026-03-19

## Scope

This closeout records the completion of the first implementation batch for
`ESP32JTAG` as a named instrument-level interface, without changing backend
action execution ownership.

Completed scope:

- add a minimal `jtag_native_api`
- integrate it into native dispatch
- surface it through instrument view and instrument doctor
- verify the change with targeted tests
- collect healthy live `ESP32JTAG` doctor/status evidence points

Out of scope:

- migrating flash/reset/debug execution out of `esp32_jtag backend`
- replacing generic control execution paths
- adding new instrument actions beyond the minimal metadata/doctor surface

## What Changed

The new interface layer is:

- [ael/instruments/jtag_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/jtag_native_api.py)

It defines:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `preflight_probe`

It now also makes the instrument-level surface more explicit by:

- exposing status domains for `network`, `gdb_remote`, `web_api`,
  `capture_subsystem`, and `monitor_targets`
- presenting `ESP32JTAG` consistently as an `instrument_family`
- documenting lifecycle ownership separate from backend action execution

Integration points:

- [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)
- [ael/instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)
- [ael/instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)

Design/implementation notes:

- [docs/esp32jtag_instrument_interface_model_memo_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_instrument_interface_model_memo_2026-03-19.md)
- [docs/esp32jtag_interface_gap_matrix_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_interface_gap_matrix_2026-03-19.md)
- [docs/jtag_native_api_minimal_spec_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/jtag_native_api_minimal_spec_2026-03-19.md)
- [docs/jtag_native_api_transition_plan_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/jtag_native_api_transition_plan_2026-03-19.md)
- [docs/jtag_native_api_implementation_review_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/jtag_native_api_implementation_review_2026-03-19.md)

## Verification

Targeted tests:

- `tests/test_jtag_native_api.py`
- `tests/test_native_api_dispatch.py`
- `tests/test_instrument_doctor.py`
- `tests/test_instrument_view.py`

Regression checks:

- `tests/test_esp32_jtag_backend.py`
- `tests/test_meter_native_api.py`
- `tests/test_esp32_meter_backend.py`
- `tests/test_esp32_meter_dispatcher.py`

Observed result:

- targeted suite: `17 passed`
- regression suite: `27 passed`

Real bench validation:

- command: `python3 -m ael instruments doctor --id esp32jtag_stm32_golden --format json`
- instance: `esp32jtag_stm32_golden @ 192.168.2.109`
- purpose: confirm that instrument-level doctor/status surfaces work against a
  live `ESP32JTAG` instance after the integration
- observed result:
  - `native_identify.status = ok`
  - `native_capabilities.status = ok`
  - `native_status.status = ok`
  - overall doctor result: `ok = false`
  - live network result:
    - `debug_remote`: timeout on `192.168.2.109:4242`
    - `control_api`: `No route to host` on `192.168.2.109:443`
  - interpretation:
    - the new instrument-level interface shape is live and readable
    - the failure was bench reachability, not a payload-shape or dispatch
      integration failure

Healthy live sample:

- command: `python3 -m ael instruments doctor --id esp32jtag_stm32f411 --format json`
- instance: `esp32jtag_stm32f411 @ 192.168.2.103`
- observed result:
  - overall doctor result: `ok = true`
  - `native_identify.status = ok`
  - `native_capabilities.status = ok`
  - `native_status.status = ok`
  - preflight checks:
    - ping: `ok`
    - TCP `192.168.2.103:4242`: `ok`
    - monitor targets: `ok`
    - logic-analyzer self-test: `ok`
  - returned target family: `M4`
  - control API `https://192.168.2.103:443`: `ok`
- interpretation:
  - the `jtag_native_api` layer is not only structurally correct
  - it now has one healthy live sample through the real
    `instrument_doctor -> native_api_dispatch -> jtag_native_api` path

Additional healthy sample:

- command: `python3 -m ael instruments doctor --id esp32jtag_g431_bench --format json`
- instance: `esp32jtag_g431_bench @ 192.168.2.62`
- observed result:
  - overall doctor result: `ok = true`
  - `native_identify.status = ok`
  - `native_capabilities.status = ok`
  - `native_status.status = ok`
  - preflight checks:
    - ping: `ok`
    - TCP `192.168.2.62:4242`: `ok`
    - monitor targets: `ok`
    - logic-analyzer self-test: `ok`
  - returned target family: `M4`
  - control API `https://192.168.2.62:443`: `ok`
- interpretation:
  - the healthy-sample set is no longer a single-instance confirmation
  - the instrument-level doctor/status surface now has at least two healthy
    live confirmations on separate `ESP32JTAG` benches

Additional healthy sample:

- command: `python3 -m ael instruments doctor --id esp32jtag_rp2040_lab --format json`
- instance: `esp32jtag_rp2040_lab @ 192.168.2.63`
- observed result:
  - overall doctor result: `ok = true`
  - `monitor_targets`: `M0+, M0+, Rescue (Attach to reset)`
  - `capture_subsystem`: `ok`
  - `web_api`: `ok`
- interpretation:
  - the expanded doctor/status model also works on the RP2040 bench path

Additional healthy sample:

- command: `python3 -m ael instruments doctor --id esp32jtag_h750_bench --format json`
- instance: `esp32jtag_h750_bench @ 192.168.2.106`
- observed result:
  - overall doctor result: `ok = true`
  - `monitor_targets`: `M7`
  - `capture_subsystem`: `ok`
  - `web_api`: `ok`
- interpretation:
  - the instrument-level interface now has healthy live evidence across
    multiple target families, not only the original F411/G431 benches

## What This Batch Proves

- `ESP32JTAG` now has a named instrument-level native API surface, not only a
  backend action package
- the instrument model is visible in inventory/describe/doctor surfaces
- the runtime presentation now explicitly shows `instrument_family = esp32jtag`
- status/doctor now expose subsystem-oriented health domains
- metadata/status/doctor can be clarified without destabilizing backend action
  execution

## Boundary After This Batch

Owned by `jtag_native_api`:

- identity
- capability-family reporting
- status
- doctor

Still owned by `esp32_jtag backend`:

- flash
- reset
- debug execution
- gpio measure execution
- transport details

## Next Step

If follow-on work continues, it should stay narrow:

- gather more real `doctor/status` evidence on a reachable `ESP32JTAG` bench
- optionally add one or two instrument-level actions such as
  `preflight_probe`
- do not move action execution out of `esp32_jtag backend` unless there is a
  concrete benefit

## Phase Decision

Do not widen the interface surface immediately.

Reason:

- the minimal metadata/status/doctor layer is now implemented and visible
- one real live doctor run confirmed the integration path
- there is now one healthy sample on `.103`
- there is now a second healthy sample on `.62`
- `preflight_probe` is now explicitly owned by `jtag_native_api`
- but that is still only a narrow confirmation sample, not broad runtime
  coverage

So the correct next phase is:

- keep collecting a small number of healthy `ESP32JTAG` doctor/status samples on
  reachable benches
- only then consider adding optional instrument-level actions
