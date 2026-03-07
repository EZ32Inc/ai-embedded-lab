# ESP32-C6 Phase-1 Extension Report

## Scope

This report documents the minimal ESP32-C6 path added by deriving from the existing ESP32-S3 flow, without broad refactor.

## ESP32-S3 References Used

- `configs/boards/esp32s3_devkit.yaml`
- `firmware/targets/esp32s3/`
- `tests/plans/esp32s3_gpio_signature.json`
- `tests/plans/esp32s3_gpio_signature_with_meter.json`
- `assets_golden/duts/esp32s3_devkit/manifest.yaml`
- `assets_golden/duts/esp32s3_devkit/gpio_signature/manifest.yaml`
- `assets_golden/duts/esp32s3_devkit/gpio_signature/firmware/`

## Files Added

- `configs/boards/esp32c6_devkit.yaml`
- `firmware/targets/esp32c6/CMakeLists.txt`
- `firmware/targets/esp32c6/main/CMakeLists.txt`
- `firmware/targets/esp32c6/main/main.c`
- `tests/plans/esp32c6_gpio_signature.json`
- `tests/plans/esp32c6_gpio_signature_with_meter.json`
- `assets_golden/duts/esp32c6_devkit/manifest.yaml`
- `assets_golden/duts/esp32c6_devkit/docs.md`
- `assets_golden/duts/esp32c6_devkit/gpio_signature/manifest.yaml`
- `assets_golden/duts/esp32c6_devkit/gpio_signature/docs.md`
- `assets_golden/duts/esp32c6_devkit/gpio_signature/firmware/CMakeLists.txt`
- `assets_golden/duts/esp32c6_devkit/gpio_signature/firmware/main/CMakeLists.txt`
- `assets_golden/duts/esp32c6_devkit/gpio_signature/firmware/main/main.c`
- `assets_golden/instruments/esp32_instrument_basic/manifest.json`

## Files Changed

- `ael/adapters/build_idf.py` (build dir and preferred ELF are now target-derived)
- `ael/adapters/build_artifacts.py` (IDF ELF path now target-derived)

## Reused Directly

- Existing run contract, strategy boundary, runner flow, evidence path, and evaluator/recovery behavior.
- Existing ESP-IDF build/flash adapters.
- Existing meter-driven connection model from ESP32-S3 plans.

## Changed for ESP32-C6

- Board identity and target string (`esp32c6`).
- Minimal C6 firmware project and DUT asset firmware.
- UART expectation tokens (`AEL_READY ESP32C6`, `AEL_DUT_READY`).
- Instrument manifest placeholder for new AP naming (`ESP32_GPIO_METER_XXXX`).

## Friction Points

- Existing IDF adapter assumptions were partially hardcoded to `esp32s3` naming.
- ESP32-C6 hardware was not available for real validation in this phase.
- Pin mapping and AP naming remain provisional until bench bring-up.

## Hardware-Dependent / Intentionally Minimal

- No hardware run executed in this phase.
- Meter AP SSID kept as placeholder prefix.
- Wiring assumptions follow ESP32-S3 pattern and require bench confirmation.
- Marked `verified.status: false` for ESP32-C6 DUT manifest.
