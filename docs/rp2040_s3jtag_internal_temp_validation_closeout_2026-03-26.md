## RP2040 S3JTAG Internal Temperature Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag.yaml`
- Test plan: `tests/plans/rp2040_internal_temp_mailbox_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage1.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GND` -> `RP2040 GND`
- No UART, TARGETIN, or local loopback jumper is required for the test logic itself
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 internal temperature mailbox firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 internal temperature ADC self-check via mailbox: PASS
- formal AEL test `tests/plans/rp2040_internal_temp_mailbox_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_21-56-53_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag`

Key evidence:
- Final formal run artifacts:
  - `runs/2026-03-26_21-56-53_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag/result.json`
  - `runs/2026-03-26_21-56-53_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_21-56-53_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag/artifacts/evidence.json`
- The DUT reported mailbox PASS at address `0x20041F00`.
- The DUT packs the average sample and spread into `detail0`, allowing later debugging without needing UART.

Implementation details validated:
- The test uses `adc_set_temp_sensor_enabled(true)`.
- The RP2040 internal temperature sensor is read on `ADC4`.
- The firmware takes `8` samples, computes:
  - average sample
  - sample spread
- PASS criteria are intentionally simple and bounded:
  - average sample must not be `0`
  - average sample must not be saturated (`>= 4095`)
  - spread must not be `0`
- Result reporting uses the AEL mailbox and does not depend on UART observe stability.

What mattered during validation:
- This is the first formal RP2040 `Stage 1` no-wire self-test beyond the Stage 0 runtime mailbox gate.
- Choosing mailbox instead of UART was important because it keeps the pass/fail path independent of the ESP32-S3 Web UART bridge.
- The run summary still shows the base board profile's generic `verify=TARGETIN` mapping in the connection digest, but the test itself does not consume TARGETIN or signal verification.

Why this test matters:
- It closes the biggest Rule-B structural gap in the RP2040 S3JTAG suite: a real Stage 1 no-wire self-test.
- It validates an internal RP2040 peripheral path rather than a bench wiring path.
- It creates a stable self-test layer between:
  - Stage 0 runtime gate
  - Stage 2 wired integration tests

Associated assets added:
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/docs.md`
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/manifest.yaml`
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/firmware/CMakeLists.txt`
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/firmware/main.c`
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/firmware/ael_mailbox.h`
- `assets_golden/duts/rp2040_pico/internal_temp_mailbox_s3jtag/firmware/pico_sdk_import.cmake`
- `tests/plans/rp2040_internal_temp_mailbox_s3jtag.json`

Conclusion:
- `RP2040` internal temperature sensing is now formally validated through the `S3JTAG` SWD + mailbox bench path.
- This test is suitable as a `Rule-B Stage 1` no-wire self-test.
- It should be run before Stage 2 wired tests when a quick internal peripheral health check is needed.
