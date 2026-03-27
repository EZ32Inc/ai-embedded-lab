## RP2040 S3JTAG PWM Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag.yaml`
- Test plan: `tests/plans/rp2040_pwm_capture_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage2.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 GPIO18/PWM_OUT` -> `S3JTAG TARGETIN GPIO15`
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 PWM golden firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 PWM signal observed through `S3JTAG TARGETIN`: PASS
- formal AEL test `tests/plans/rp2040_pwm_capture_with_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_21-25-33_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag`

Key evidence:
- PWM firmware built successfully at `artifacts/build_rp2040_pwm_capture_s3jtag/pico_pwm_capture_s3jtag.elf`
- Final verification reported:
  - `state=toggle`
  - `transitions=498`
  - `estimated_hz=995`
- Final formal run artifacts:
  - `runs/2026-03-26_21-25-33_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag/result.json`
  - `runs/2026-03-26_21-25-33_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_21-25-33_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag/artifacts/evidence.json`

Implementation details validated:
- PWM output uses `GPIO18`
- RP2040 hardware PWM is configured for approximately `1 kHz`
- target duty is `50%`
- the validation path is pure `TARGETIN` frequency/duty measurement; it does not depend on the Web UART bridge

What mattered during validation:
- This test is a cleaner `Stage 2` peripheral validation than the UART-backed tests because the pass/fail path does not depend on the ESP32-S3 Web UART observer.
- The only required external wiring change relative to the base S3JTAG GPIO suite is:
  - `RP2040 GPIO18/PWM_OUT` -> `S3JTAG TARGETIN GPIO15`

Observed bench behavior:
- One initial attempt failed at `preflight` because the `esp32jtag_0F91` AP had dropped and the host was no longer associated.
- After reconnecting to the AP, the exact same test passed without changing the PWM firmware or plan.
- This indicates the PWM signal path itself is robust; the transient failure was bench connectivity, not target behavior.

Associated assets added:
- `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/docs.md`
- `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/manifest.yaml`
- `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/firmware/CMakeLists.txt`
- `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/firmware/main.c`
- `assets_golden/duts/rp2040_pico/pwm_capture_s3jtag/firmware/pico_sdk_import.cmake`
- `tests/plans/rp2040_pwm_capture_with_s3jtag.json`

Conclusion:
- `RP2040 GPIO18` hardware PWM is now validated through the `S3JTAG` SWD + TARGETIN bench path.
- This test is suitable as a `Rule-B Stage 2` exercised peripheral validation.
- The validated wiring contract is minimal and explicit:
  - `GPIO18/PWM_OUT -> TARGETIN(GPIO15)`
