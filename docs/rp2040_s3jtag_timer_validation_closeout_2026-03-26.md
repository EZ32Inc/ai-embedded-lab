## RP2040 S3JTAG Timer Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag.yaml`
- Test plan: `tests/plans/rp2040_timer_mailbox_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage1.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GND` -> `RP2040 GND`
- No UART, TARGETIN, or local loopback jumper is required for the test logic itself
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 timer mailbox firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 timer callback self-check via mailbox: PASS
- formal AEL test `tests/plans/rp2040_timer_mailbox_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_22-02-00_rp2040_pico_s3jtag_rp2040_timer_mailbox_s3jtag`

Key evidence:
- Final formal run artifacts:
  - `runs/2026-03-26_22-02-00_rp2040_pico_s3jtag_rp2040_timer_mailbox_s3jtag/result.json`
  - `runs/2026-03-26_22-02-00_rp2040_pico_s3jtag_rp2040_timer_mailbox_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_22-02-00_rp2040_pico_s3jtag_rp2040_timer_mailbox_s3jtag/artifacts/evidence.json`
- The DUT reported mailbox PASS at address `0x20041F00`.
- `detail0` exposes the timer tick count before PASS, then packs tick count and post-pass heartbeat for later debugging.

Implementation details validated:
- The firmware uses `add_repeating_timer_ms(100, ...)`.
- The repeating timer callback increments a bounded counter every `100 ms`.
- PASS is written after `10` callbacks, giving an expected pass point of about `1 s`.
- If the timer cannot be armed, the firmware reports mailbox FAIL with `error_code = 1`.
- Result reporting uses the AEL mailbox and does not depend on UART observe stability.

What mattered during validation:
- This test extends the RP2040 `Stage 1` no-wire layer with a timer-focused self-check rather than another wiring exercise.
- Using mailbox instead of UART keeps the test independent from the ESP32-S3 Web UART bridge and makes it suitable as a clean pre-stage health check.
- The run summary still shows the base board profile's generic `verify=TARGETIN` mapping in the connection digest, but the test itself does not consume TARGETIN or signal verification.

Why this test matters:
- It adds a second real `Rule-B Stage 1` no-wire self-test for `RP2040 + S3JTAG`.
- It validates the RP2040 timer/alarm callback path instead of a bench wiring path.
- It strengthens the self-test layer between:
  - Stage 0 runtime gate
  - Stage 2 wired integration tests

Associated assets added:
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/docs.md`
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/manifest.yaml`
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/firmware/CMakeLists.txt`
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/firmware/main.c`
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/firmware/ael_mailbox.h`
- `assets_golden/duts/rp2040_pico/timer_mailbox_s3jtag/firmware/pico_sdk_import.cmake`
- `tests/plans/rp2040_timer_mailbox_s3jtag.json`

Conclusion:
- `RP2040` timer callback behavior is now formally validated through the `S3JTAG` SWD + mailbox bench path.
- This test is suitable as a `Rule-B Stage 1` no-wire self-test.
- It should be run before Stage 2 wired tests when a quick internal scheduler/timer health check is needed.
