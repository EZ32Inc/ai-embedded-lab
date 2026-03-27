## RP2040 S3JTAG GPIO Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag.yaml`
- Test plan: `tests/plans/rp2040_gpio_signature_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/gpio_signature_s3jtag/firmware`
- Supporting firmware-side validation hook: `test_targetin_detect` on the `esp32s3_devkit` board profile

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GND` -> `RP2040 GND`
- `RP2040 GPIO18` -> `S3JTAG TARGETIN GPIO15`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 golden firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 post-flash image verify via `compare-sections`: PASS
- firmware-side `TARGETIN(GPIO15)` detect of RP2040 `GPIO18` 1 kHz output: PASS
- formal AEL smoke pack `packs/smoke_rp2040_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_05-54-03_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag`

Key evidence:
- RP2040 golden firmware built successfully at `artifacts/build_rp2040_gpio_signature_s3jtag/pico_gpio_signature_s3jtag.elf`
- `arm-none-eabi-gdb` over `192.168.4.1:4242` completed `monitor swd_scan`, `attach 1`, `load`, and `compare-sections` without image mismatch
- Formal AEL pack run completed with `PASS: Run verified` and `key_checks_passed=gpio.signal`
- Final formal run artifacts:
  - `runs/2026-03-26_05-54-03_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag/result.json`
  - `runs/2026-03-26_05-54-03_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag/artifacts/verify_result.json`
- Final live `TARGETIN` result:

```json
{"test":"test_targetin_detect","result":"pass","pin":15,"state":"toggle","samples":9343,"high":4646,"low":4697,"transitions":500,"estimated_hz":999}
```

What failed first and why:
- The generic `esp32s3_devkit` path does not have the FPGA-backed logic capture surface used by the original `ESP32JTAG` board, so trying to reuse old instant-capture assumptions was the wrong path.
- RP2040 firmware build initially failed because `PICO_SDK_PATH` was not set to the real SDK location and the old CMake cache preserved a host `cc` toolchain choice.
- Native USB flashing on the S3 became unreliable once the board stopped running a healthy application image. `esptool --before usb_reset` hit write timeouts until the board was forced into download mode manually.
- After recovery flashing, the host Wi-Fi adapter did not always rejoin the S3 AP automatically, so `192.168.4.1` appeared down until the saved NetworkManager profile was brought back up.
- The first formal pack attempts still failed after bench recovery because AEL runtime layers were assuming LA-style capture semantics in two places:
  - `preflight` still treated the path as logic-analyzer self-test
  - `check_signal` still treated `TARGETIN` as an LA bit name

Evidence that separated false leads from the real path:
- `esp-idf/export.sh` was not the missing ingredient. It did not provide `PICO_SDK_PATH`; the real fix was setting `PICO_SDK_PATH=/nvme1t/github/pico-sdk` and clearing the stale build directory.
- SWD connectivity was already known-good because the earlier `monitor swd_scan` path consistently found the RP2040 targets. The missing piece for this suite was target signal verification, not SWD attach itself.
- Once `test_targetin_detect` sampled `GPIO15` directly on the S3, the expected ~1 kHz signal appeared immediately, proving the bench path without needing FPGA capture hardware.
- After the AEL-side fixes, the formal pack moved from `preflight` failure to `check_signal` failure and finally to `PASS`, which isolated the remaining issues to runtime semantics rather than firmware or wiring.

Last-known-good recovery steps:
- RP2040 build:
  - `export PICO_SDK_PATH=/nvme1t/github/pico-sdk`
  - `export PATH=/nvme1t/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin:$PATH`
  - remove `artifacts/build_rp2040_gpio_signature_s3jtag` before reconfiguring if toolchain cache drift is suspected
- If S3 native USB flashing times out:
  1. hold `BOOT`
  2. tap `RESET`
  3. release `RESET`
  4. release `BOOT`
  5. flash again with `esptool` while the board is in ROM download mode
  6. press `RESET` once more after flashing to leave download mode
- If the host does not return to the AP automatically:
  - `nmcli connection up esp32jtag_0F91 ifname wlx90de80a53084`

AEL-side fixes required for the formal pack path:
- `b2ebf42` `Support TARGETIN preflight on S3JTAG`
- `bfdd76a` `Support TARGETIN signal verification on S3JTAG`

Conclusion:
- The `S3JTAG` pattern is now validated for `RP2040` as a combined SWD flash + single-pin signal-detect instrument path.
- This path is now proven both as an ad hoc live bench workflow and as a formal AEL pack run through `packs/smoke_rp2040_s3jtag.json`.
- This path is not a logic-analyzer replacement. Its validated scope is: program the target over SWD, then confirm target-side GPIO activity through `TARGETIN`.
- The correct reusable abstraction for this bench is `S3JTAG + RP2040 signal validation`, not `ESP32JTAG FPGA capture` reused under a new board name.
