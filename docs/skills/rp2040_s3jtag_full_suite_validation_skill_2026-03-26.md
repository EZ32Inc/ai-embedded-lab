# RP2040 S3JTAG Full Suite Validation Skill

## Purpose

Capture the reusable workflow for validating the complete `RP2040 + S3JTAG` 12-test suite on one fixed bench wiring.

This skill matters because the suite only became a true fixed-wiring full pack after the `TARGETIN` signal tests were retargeted to `RP2040 GPIO18`, aligning them with the PWM test.

## Trigger / When To Use

Use this skill when:
- the target is `RP2040 Pico`
- the control instrument is `S3JTAG`
- you want to validate the whole Rule-B suite rather than a single test
- you need the exact firmware revision used by the suite recorded in the closeout

## Validated Scope

Validated pack on 2026-03-26:
- `packs/rp2040_s3jtag_full.json`
- pack run: `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag`
- result: PASS

Validated `esp32jtag_firmware` revision:
- repo: `/nvme1t/work/esp32jtag_firmware`
- commit: `5a140cab59306f687e6affd4808df5be0ec8a779`
- summary: `5a140ca Add UART RX GPIO diagnostic hook`

Validated fixed wiring:
- `S3JTAG GPIO4` -> `RP2040 SWCLK`
- `S3JTAG GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GPIO7` <- `RP2040 GPIO0/UART0_TX`
- `S3JTAG GPIO6` -> `RP2040 GPIO1/UART0_RX`
- `S3JTAG GPIO15 TARGETIN` <- `RP2040 GPIO18`
- `RP2040 GPIO3/SPI0_TX` -> `RP2040 GPIO4/SPI0_RX`
- `RP2040 GPIO16` -> `RP2040 GPIO17`
- common ground

## Core Flow

1. Confirm host connectivity to `esp32jtag_0F91`.
2. Confirm `192.168.4.1:4242` and `https://192.168.4.1:443` are reachable.
3. Confirm the bench uses the fixed full-suite wiring above.
4. Record the current `esp32jtag_firmware` commit with:
   `git -C /nvme1t/work/esp32jtag_firmware rev-parse HEAD`
5. Run the full pack:

```bash
python3 -m ael pack --pack packs/rp2040_s3jtag_full.json --board rp2040_pico_s3jtag
```

6. Archive the pack-level artifacts from the latest `pack_runs/...` directory.
7. Record the firmware commit hash in the suite closeout.

## Expected Result Shape

Expected success shape:
- pack exits `0`
- `pack_result.json` reports `ok: true`
- all 12 test entries show `ok: true`

## Recovery Rules

If `TARGETIN` family tests fail while PWM passes:
- treat the suite contract as drifted and verify that the GPIO signal tests still target `GPIO18`, not an older `GPIO16` assumption

If UART tests fail while mailbox/TARGETIN pass:
- verify the UART pair remains:
  - `GPIO0 -> GPIO7`
  - `GPIO1 -> GPIO6`

If the firmware repo shows only untracked build directories:
- do not create a fake firmware commit
- record the current validated committed revision instead

## Why This Skill Is Valuable

It gives one reproducible, fixed-wiring suite for the RP2040 bench and ties that suite result to a concrete S3JTAG firmware revision. That avoids two common failure modes:
- claiming a full-suite pass across mixed wiring contracts
- losing track of which ESP32-S3 firmware revision actually backed the validated run
