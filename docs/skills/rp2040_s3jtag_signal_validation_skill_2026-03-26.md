# RP2040 S3JTAG Signal Validation Skill

## Purpose

Capture the reusable workflow for validating an `RP2040` target through the `S3JTAG` instrument path when the instrument is a generic `ESP32-S3 devkit` without FPGA-backed capture hardware.

This skill exists because the successful bench pattern was not “reuse ESP32JTAG logic capture on a new board”. The working pattern was narrower and simpler:
- flash the target over SWD
- make the target emit a known GPIO signal
- detect that signal through `TARGETIN` on the S3 instrument

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG` or another generic `esp32s3_devkit`-class probe
- SWD flashing works but waveform or logic-capture assumptions do not
- a target can export a single GPIO heartbeat, square wave, or level signal
- the goal is to prove `flash + target-side signal detect`, not deep sampled capture

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- common ground
- target output GPIO -> `S3JTAG TARGETIN GPIO15`

Validated target on 2026-03-26:
- `RP2040 Pico`
- target output: `GPIO16`
- signal: about `1 kHz` square wave

## Why This Skill Matters

The false lead in this work was treating the generic S3 board as if it still exposed the original FPGA-backed `ESP32JTAG` capture path. It does not.

The reusable lesson is:
- keep SWD programming on the BMP/GDB path
- move signal verification to a direct GPIO sampling path on the S3 firmware
- do not wait for logic-analyzer parity before validating a simpler instrument capability

## Preconditions

Required host environment for the RP2040 golden build:
- `export PICO_SDK_PATH=/nvme1t/github/pico-sdk`
- `export PATH=/nvme1t/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin:$PATH`

Required bench assumptions:
- host is joined to the instrument AP
- instrument API is reachable at `https://192.168.4.1`
- BMP/GDB remote is reachable at `192.168.4.1:4242`
- target output pin is wired to `TARGETIN(GPIO15)`

## Core Flow

1. Build the RP2040 golden firmware with a known signal output.
2. Remove any stale CMake build directory first if toolchain drift is suspected.
3. Connect to the instrument over BMP/GDB remote and confirm `monitor swd_scan` sees the target.
4. `load` the new target image and run `compare-sections`.
5. Ensure the S3 firmware exposes `test_targetin_detect` or an equivalent direct sampling path on `GPIO15`.
6. Trigger the detect test over the instrument web API.
7. Confirm the returned JSON shows toggling behavior and a plausible frequency estimate.
8. Record the result as `flash + detect`, not as full waveform capture.

## Canonical Commands

RP2040 build:

```bash
rm -rf artifacts/build_rp2040_gpio_signature_s3jtag
export PICO_SDK_PATH=/nvme1t/github/pico-sdk
export PATH=/nvme1t/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin:$PATH
cmake -S assets_golden/duts/rp2040_pico/gpio_signature_s3jtag/firmware -B artifacts/build_rp2040_gpio_signature_s3jtag
cmake --build artifacts/build_rp2040_gpio_signature_s3jtag -j4
```

Flash and verify through `S3JTAG`:

```bash
arm-none-eabi-gdb -q artifacts/build_rp2040_gpio_signature_s3jtag/pico_gpio_signature_s3jtag.elf \
  -ex 'set pagination off' \
  -ex 'target extended-remote 192.168.4.1:4242' \
  -ex 'monitor swd_scan' \
  -ex 'attach 1' \
  -ex 'load' \
  -ex 'compare-sections' \
  -ex 'quit'
```

Detect target output on `TARGETIN`:

```bash
curl -k -sS -u admin:admin -H 'Content-Type: application/json' \
  -d '{"test_type":"test_targetin_detect"}' \
  https://192.168.4.1/test/start

curl -k -sS -u admin:admin https://192.168.4.1/test/status
curl -k -sS -u admin:admin https://192.168.4.1/test/result
```

Expected result shape:

```json
{"test":"test_targetin_detect","result":"pass","pin":15,"state":"toggle","estimated_hz":999}
```

## Recovery Rules

If RP2040 build fails unexpectedly:
- verify `PICO_SDK_PATH` points to `/nvme1t/github/pico-sdk`
- remove the stale build directory before rerunning `cmake`
- verify the ARM GNU toolchain bin directory is on `PATH`

If S3 native USB flashing hits `Write timeout`:
1. hold `BOOT`
2. tap `RESET`
3. release `RESET`
4. release `BOOT`
5. flash while the board is in ROM download mode
6. press `RESET` after flashing so the application boots normally

If the host does not return to the instrument AP automatically:
- run `nmcli connection up esp32jtag_0F91 ifname wlx90de80a53084`

## Non-Goals

This skill is not for:
- FPGA-backed instant capture
- proving analog waveform quality
- proving multi-channel timing relationships
- replacing a real logic analyzer

## Success Criteria

This skill has succeeded when:
- the target image is built from the `gpio_signature_s3jtag` asset
- the image is flashed through `S3JTAG` over SWD
- `compare-sections` succeeds
- `test_targetin_detect` reports toggling on `GPIO15`
- the reported frequency is consistent with the target firmware output

## Why This Was Easy To Miss

The misleading assumption was that a new board profile should preserve the old instrument semantics. That was too strict.

The better rule is:
- preserve the validated user outcome if possible
- but shrink the mechanism to the simplest hardware truth that the new board actually supports

For `S3JTAG`, the hardware truth is `SWD + single digital input detect`, not `SWD + FPGA capture`.
