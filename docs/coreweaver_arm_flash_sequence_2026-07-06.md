# CoreWeaver ARM Flash Sequence

Date: 2026-07-06

## Problem

Some CoreWeaver ARM/Cortex targets can be programmed successfully but remain
halted after `load` if the post-load GDB sequence uses a generic reset command.
The visible symptom is:

- flash and verify pass
- the LED program does not run immediately
- the program runs only after a target power cycle

This is the same issue previously debugged on STM32F401/F411. For STM32 targets,
the working sequence was not `monitor reset run`; it was a second attach
followed by detach.

RP2040 is an exception. The RP2040 Pico on CoreWeaver channel 2 was later
validated with the older RP2040 golden-run shape:
`load`, `monitor reset run`, `continue`, `detach`. See
`docs/coreweaver_stm32_rp2040_flash_script_fix_2026-07-06.md`.

## Working Pattern

Use this post-load pattern for CoreWeaver STM32 ARM/Cortex targets:

```text
monitor swd_scan
file <firmware.elf>
attach 1
load
compare-sections
attach 1
detach
```

Do not use this as the normal post-load step for these targets:

```text
monitor reset
monitor reset run
continue
```

Those commands can leave the user-visible firmware stopped until the board is
power-cycled.

## Helper

Use:

```sh
python3 tools/coreweaver_flash_arm.py --channel <n> path/to/firmware.elf
```

For the fixed STM32H503 on channel 4:

```sh
python3 tools/coreweaver_flash_arm.py \
  --host 192.168.4.1 \
  --channel 4 \
  --frequency 100000 \
  artifacts/build_stm32h503_pc13_blinky/stm32h503_pc13_blinky.elf
```

For RP2040 on channel 2, do not use the STM32 post-load sequence. Lower the
debug speed before scan and use the RP2040-specific reset/continue/detach
sequence:

```sh
arm-none-eabi-gdb -q --nx --batch \
  -ex "set remotetimeout 15" \
  -ex "target extended-remote 192.168.4.1:4244" \
  -ex "monitor frequency 1000" \
  -ex "monitor swd_scan" \
  -ex "file artifacts/build_rp2040_pico_s3jtag/pico_blink.elf" \
  -ex "attach 1" \
  -ex "load" \
  -ex "monitor reset run" \
  -ex "continue" \
  -ex "detach" \
  -ex "quit"
```

For STM32H750 on channel 3:

```sh
python3 tools/coreweaver_flash_arm.py \
  --channel 3 \
  firmware/targets/stm32h750_pc0_pc1_pc2_blinky/build/stm32h750_pc0_pc1_pc2_blinky.elf
```

For RP2354/RP2350 on channel 6:

```sh
python3 tools/coreweaver_flash_arm.py \
  --channel 6 \
  artifacts/build_rp2354_coreweaver_blinky/rp2354_coreweaver_blinky.elf
```

## Scope

This note applies to STM32 ARM/Cortex targets on CoreWeaver, including
STM32F401, STM32F411, STM32H503, and STM32H750. RP2040 and RP2354/RP2350 need
their own target-family-specific handling.

It does not apply to CH32V006 or CH32V305. Those WCH RISC-V paths use different
debug transports and have separate flash/run handling.

## 2026-07-06 CoreWeaver Fixed-MCU Validation

The new CoreWeaver board was flashed through the ESP32-S3 JTAG firmware at
`192.168.4.1`. The fixed MCU channels are channel 4 through channel 7:

| Channel | MCU | Result |
| --- | --- | --- |
| 4 | STM32H503 | SWD detected `STM32H5 M33`; `stm32h503_pc13_blinky.elf` loaded and verified; LED blinked immediately after flash. |
| 5 | CH32V305 | WCH SWIO detected `CH32V (unknown variant) QingKe V4`; `ch32v305_pc2_blinky.elf` loaded and verified; LED blinked immediately after flash. |
| 6 | RP2350 | Target voltage was present, but SWD scan failed, including connect-under-reset; do not flash until the debug wiring is fixed. |
| 7 | CH32V006 | WCH SWIO detected `CH32V006K8U6 QingKe V2`; `ch32v006_pd2_blinky.elf` loaded and verified after lowering debug frequency; LED blinked immediately after flash. |

The key behavior confirmed by visual inspection was that the STM32H503,
CH32V305, and CH32V006 programs started running immediately after flashing.
They no longer require a target power cycle before the LED blink starts.

## CH32V006 Debug Frequency

CH32V006 channel 7 was not reliable at the default scan/programming speed. With
the added PD1 pull-up, target discovery was stable, but the first `load` at a
requested 100 kHz frequency reported a `.text` mismatch during
`compare-sections`.

Later testing on another CoreWeaver board showed an additional GDB remote issue:
old WCH GDB 8.3 does not cleanly parse the CH32V006 `rv32emc` target
description, and may report `Truncated register 8`, `Error writing data to
flash`, or false `compare-sections` mismatches. See
`docs/coreweaver_ch32v006_gdb_remote_issue_2026-07-06.md`.

Use a lower requested frequency for CH32V006 flashing:

```sh
/nvme1t/wch-riscv-gcc/bin/riscv-none-embed-gdb -q --nx --batch \
  -ex "target extended-remote 192.168.4.1:4249" \
  -ex "monitor frequency 50000" \
  -ex "monitor swd_scan" \
  -ex "attach 1" \
  -ex "file artifacts/build_ch32v006_pd2_blinky/ch32v006_pd2_blinky.elf" \
  -ex "load" \
  -ex "compare-sections" \
  -ex "monitor reset run" \
  -ex "detach" \
  -ex "quit"
```

On the validated board, `monitor frequency 50000` selected an actual debug
frequency of about 99 kHz and made `.init`, `.text`, and `.data` all match on
readback.
