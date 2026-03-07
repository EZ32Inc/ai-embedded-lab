# ESP32-C6 Phase-1 Extension Report

## Scope

This report documents the existing minimal ESP32-C6 path (derived from ESP32-S3), then the follow-up staged-execution normalization performed in prompt_25.

Current staged model used in this update:

- plan
- pre-flight
- run
- check
- report

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
- Existing staged execution controls (`--until-stage plan|pre-flight|report`) in `ael run`.

## Changed for ESP32-C6

- Board identity and target string (`esp32c6`).
- Minimal C6 firmware project and DUT asset firmware.
- UART expectation tokens (`AEL_READY ESP32C6`, `AEL_DUT_READY`).
- Instrument manifest placeholder for new AP naming (`ESP32_GPIO_METER_XXXX`).

## What Existed Before Prompt_25

- Draft ESP32-C6 board/config/firmware/plans/assets were already present.
- Skill/report metadata and templates were already drafted.
- IDF artifact name generalization was already implemented in adapter layer.

## Prompt_25 Inspection and Normalization

Kept as-is after inspection:

- `configs/boards/esp32c6_devkit.yaml`
- `firmware/targets/esp32c6/*`
- `tests/plans/esp32c6_gpio_signature.json`
- `tests/plans/esp32c6_gpio_signature_with_meter.json`
- `assets_golden/duts/esp32c6_devkit/*`
- `assets_golden/instruments/esp32_instrument_basic/manifest.json`
- `ael/adapters/build_idf.py`
- `ael/adapters/build_artifacts.py`

Normalization outcome:

- No structural code refactor required.
- Existing target-derived IDF artifact logic was confirmed necessary and correct.
- Stage boundary usage for ESP32-C6 was validated using `--until-stage`.

## Stage Completion Status (Prompt_25)

- `plan`: completed
  - ESP32-C6 planning artifacts resolve and execute in plan-only mode.
  - Naming/layout consistency with ESP32-S3 reference path confirmed.
- `pre-flight`: completed as far as practical in this environment
  - AEL pre-flight stage executed with ESP32-C6 config and probe path.
  - Host-side ESP-IDF target configuration check (`idf.py set-target esp32c6 reconfigure`) succeeded.
- `run`: deferred
- `check`: deferred
- `report`: deferred as runtime-stage objective (this document is design/reporting, not hardware report stage completion).

## Validation Actually Executed

- `python3 -m ael run --board esp32c6_devkit --test tests/plans/esp32c6_gpio_signature.json --probe configs/esp32jtag.yaml --until-stage plan --quiet` -> PASS
- `python3 -m ael run --board esp32c6_devkit --test tests/plans/esp32c6_gpio_signature.json --probe configs/esp32jtag.yaml --until-stage pre-flight --quiet` -> PASS
- `idf.py -C firmware/targets/esp32c6 -B /tmp/ael_esp32c6_preflight set-target esp32c6 reconfigure` -> PASS
- `PYTHONPATH=. pytest -q tests/test_staged_execution.py tests/test_strategy_resolver.py` -> PASS

Notes:

- A non-escalated pre-flight invocation initially failed due sandbox network restrictions (`Operation not permitted`), then passed with approved escalated execution.

## Friction Points

- Existing IDF adapter assumptions were partially hardcoded to `esp32s3` naming.
- ESP32-C6 hardware was not available for real validation in this phase.
- Pin mapping and AP naming remain provisional until bench bring-up.
- Pre-flight bench network checks depend on execution permissions in this environment.

## Hardware-Dependent / Intentionally Minimal

- No ESP32-C6 hardware-attached `run/check` execution was performed in this phase.
- Meter AP SSID kept as placeholder prefix.
- Wiring assumptions follow ESP32-S3 pattern and require bench confirmation.
- Marked `verified.status: false` for ESP32-C6 DUT manifest.
