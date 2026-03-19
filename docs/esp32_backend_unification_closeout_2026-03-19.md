# ESP32 Backend Unification Closeout

Date: 2026-03-19

## Scope

This closeout records the completion of three bounded follow-on batches:

- continue `ESP32 meter` consumer migration onto the unified backend
- capture closeout and reusable skills for the ESP32 instrument unification work
- align `USB-UART bridge` to the same package-style backend shape used by
  `esp32_jtag`, `esp32_meter`, and `stlink_backend`
- confirm a real meter-backed runtime path still passes after the migration

## What Changed

### ESP32 Meter

The meter line now has:

- unified backend package under
  [ael/instruments/backends/esp32_meter](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_meter)
- dispatcher driver registration through
  [ael/instruments/dispatcher.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/dispatcher.py)
- runtime adapter-registry usage for:
  - `measure.digital`
  - `measure.voltage`
- native meter action wrappers now execute through the backend instead of calling
  the low-level TCP adapter directly:
  [ael/instruments/meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)

Current boundary:

- metadata / doctor / reachability remain in native/provision code
- action execution now flows through the unified backend boundary
- default/runtime meter-backed flows continue to identify themselves as
  `meter_native_api`, but those action calls now bridge onto `esp32_meter`

### USB-UART Bridge

The USB-UART bridge is now package-aligned:

- new package:
  [ael/instruments/backends/usb_uart_bridge](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/usb_uart_bridge)

This was a shape alignment only. It did not introduce new USB-UART capabilities.

### Legacy ESP Remote JTAG

The old `esp_remote_jtag` driver is now explicitly legacy:

- [ael/instruments/backends/esp_remote_jtag.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp_remote_jtag.py)

It no longer owns a mixed implementation. It forwards action execution to:

- `esp32_jtag`
- `esp32_meter`

## Verification

The following tests were used to validate the change:

- `tests/test_esp32_meter_backend.py`
- `tests/test_esp32_meter_dispatcher.py`
- `tests/test_meter_native_api.py`
- `tests/test_adapter_registry_instrument_backend.py`
- `tests/test_phase2_native_api_routing.py`
- `tests/test_usb_uart_bridge_backend.py`
- `tests/test_esp_remote_jtag_shim.py`

Live validation:

- `esp32c6_gpio_signature_with_meter`
  - board: `esp32c6_devkit`
  - instrument: `esp32s3_dev_c_meter @ 192.168.4.1:9000`
  - result: `PASS`
  - run id: `2026-03-19_10-34-45_esp32c6_devkit_esp32c6_gpio_signature_with_meter`

## Reusable Conclusions

- meter action migration can be done narrowly by moving action execution behind a
  backend wrapper while leaving provision / doctor code in place
- runtime path labels do not need to be renamed immediately if the underlying
  action execution boundary has already been migrated cleanly
- package-shape alignment for legacy backends can be done with a compatibility
  shim, without forcing immediate consumer rewrites
