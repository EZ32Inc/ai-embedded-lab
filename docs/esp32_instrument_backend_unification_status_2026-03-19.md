# ESP32 Instrument Backend Unification Status

Date: 2026-03-19

## Purpose

Record the current unification status for the two ESP32-based instrument lines:

- `ESP32JTAG`
- `ESP32-S3 meter`

The question is not whether they are usable today, but whether they are already
packaged behind the same kind of unified instrument backend boundary used by
newer IAM-style instrument backends such as `stlink` and `esp32_jtag`.

## Short Answer

- `ESP32JTAG`: yes, complete at the backend-package level
- `ESP32JTAG`: yes, now also has a minimal instrument-level native API surface
  for identity / status / doctor / preflight
- `ESP32-S3 meter`: action-path unification is now complete; metadata and
  provision paths still remain native/provision scoped

## ESP32JTAG Status

`ESP32JTAG` has a reference-style IAM backend package:

- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)
- [ael/instruments/backends/esp32_jtag/transport.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/transport.py)
- [ael/instruments/backends/esp32_jtag/capability.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/capability.py)
- action modules under
  [ael/instruments/backends/esp32_jtag/actions](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/actions)

Dispatcher integration is explicit:

- [ael/instruments/dispatcher.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/dispatcher.py)
  maps `esp32_jtag` to the backend package

Current result:

- flash/reset/gpio_measure are integrated through the unified instrument backend path
- debug placeholder actions exist
- this line is already in the same packaging family as `stlink_backend`
- a minimal instrument-level native API now exists for:
  - `identify`
  - `get_capabilities`
  - `get_status`
  - `doctor`
  - `preflight_probe`
- healthy live doctor samples now exist for:
  - `esp32jtag_stm32f411 @ 192.168.2.103`
  - `esp32jtag_g431_bench @ 192.168.2.62`

Conclusion:

- `ESP32JTAG` can be treated as unified both at the backend-package level and
  at the minimal instrument-interface level

## ESP32-S3 Meter Status

The meter action path is now packaged in the same backend family.

Current active pieces are:

- backend package:
  [ael/instruments/backends/esp32_meter](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_meter)
- dispatcher registration:
  [ael/instruments/dispatcher.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/dispatcher.py)
- native API wrapper, now action-bridged to the backend:
  [ael/instruments/meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)
- adapter-registry runtime backend:
  [ael/adapter_registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapter_registry.py)
- default/runtime consumer path:
  [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)

What still remains outside the backend package on purpose:

- reachability / doctor / status:
  [ael/instruments/provision.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/provision.py)
- native dispatch metadata path:
  [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)

Conclusion:

- the meter action path is now in the unified backend family
- provision and metadata logic remain bounded native/provision code
- a real meter-backed runtime path has been revalidated after migration

## Current Boundary

The current state is mixed:

- `ESP32JTAG` is in the newer unified backend family
- `ST-Link` is in the newer unified backend family
- `ESP32-S3 meter` action execution is in the newer unified backend family
- `USB-UART bridge` is now package-aligned with a compatibility shim
- `esp_remote_jtag` is now explicitly a legacy compatibility shim over
  `esp32_jtag` + `esp32_meter`

So the answer to "is instrument packaging unified already?" is:

- for `ESP32JTAG`: yes
- for `ESP32-S3 meter`: yes for action execution; metadata/provision still stay native

## Current Boundary Decision

The chosen boundary is now explicit:

- backend package owns action execution
- native/provision code owns status, doctor, and reachability
- runtime health/reporting code may still label the path as `meter_native_api`
  while the action execution itself is delegated to `esp32_meter`

This gives packaging parity without reopening the whole meter architecture.
