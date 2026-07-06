# CoreWeaver CH32V006 GDB Remote Issue

Date: 2026-07-06

## Context

A new CoreWeaver board was flashed with the latest ESP32JTAG firmware and then
tested through the fixed MCU channels:

| Channel | Port | Target | Result |
| --- | --- | --- | --- |
| 4 | 4246 | STM32H503 | Detected, flashed, compare matched |
| 5 | 4247 | CH32V305 | Detected, flashed, compare matched |
| 6 | 4248 | RP2354/RP2350 | Detected, flashed, compare matched |
| 7 | 4249 | CH32V006 | Detected, but GDB load/compare was unstable |

The CH32V006 path used the same RISC-V GDB as the CH32V305 path:

```text
/nvme1t/wch-riscv-gcc/bin/riscv-none-embed-gdb
GNU gdb 8.3
```

This was not caused by accidentally using a different GDB for CH32V006.

## Symptom

CH32V006 target discovery worked:

```text
Debug iface frequency set to 99391Hz
Target voltage: 3.3V
Available Targets:
No. Att Driver
 1      CH32V006K8U6 QingKe V2
```

But the normal flash path sometimes failed:

```text
Error writing data to flash
```

or completed `load` but failed readback:

```text
Section .init, range 0x0 -- 0xa8: matched.
Section .text, range 0xa8 -- 0x89c: MIS-MATCHED!
Section .data, range 0x89c -- 0x8b4: matched.
```

The same session also printed GDB/remote register-description warnings:

```text
Target description specified unknown architecture "riscv:rv32emc"
Could not load XML target description; ignoring
Truncated register 8 in remote 'g' packet
Could not fetch register "pc"; remote failure reply 'EFF'
```

## Why CH32V305 Looked Better

CH32V305 used the same GDB and also printed a target-description warning:

```text
Target description specified unknown architecture "riscv:rv32imafc"
Could not load XML target description; ignoring
Truncated register 16 in remote 'g' packet
```

However, CH32V305 still completed `load` and `compare-sections`:

```text
Section .init, range 0x0 -- 0x4: matched.
Section .vector, range 0x4 -- 0x1c0: matched.
Section .text, range 0x1c0 -- 0x3ac: matched.
```

The practical difference is that CH32V006 reports `rv32emc` / RV32E-style state,
which exposes a smaller register set and triggers a worse mismatch with this old
GDB 8.3 and the Black Magic remote register packet. CH32V305 also has a warning,
but its register/readback path did not fail hard in this run.

## Useful Workaround

Before connecting, force GDB to use a generic RV32 architecture:

```sh
/nvme1t/wch-riscv-gcc/bin/riscv-none-embed-gdb -q --nx --batch \
  -ex "set architecture riscv:rv32" \
  -ex "set remotetimeout 30" \
  -ex "target extended-remote 192.168.4.1:4249" \
  -ex "monitor frequency 50000" \
  -ex "monitor swd_scan" \
  -ex "attach 1" \
  -ex "file artifacts/build_ch32v006_pd2_blinky/ch32v006_pd2_blinky.elf" \
  -ex "load" \
  -ex "monitor ch32v006_flash_status" \
  -ex "monitor reset run" \
  -ex "detach" \
  -ex "quit"
```

With `set architecture riscv:rv32`, `load` completed all sections:

```text
Loading section .init, size 0xa8 lma 0x0
Loading section .text, size 0x7f4 lma 0xa8
Loading section .data, size 0x18 lma 0x89c
Start address 0x0, load size 2228
```

The CH32V006 flash driver status then reported no internal flash failure:

```text
ch32v006 flash status: erase=1 write=35 load32=560 stage=0x14 fail=0x00
last SR=0x00009000 CR=0x00008080 read[0x00000880]=0xcf088d5d
```

This is a workaround, not a complete fix. `compare-sections` can still report a
`.text` mismatch because the readback/register path is still affected by the
same GDB remote description problem.

## Debugging Order For Next Time

When CH32V006 fails again, start here:

1. Confirm physical debug entry first:

```text
monitor frequency 50000
monitor swd_scan
```

Expected target:

```text
CH32V006K8U6 QingKe V2
```

2. If GDB prints `rv32emc` / `Truncated register 8`, retry with:

```text
set architecture riscv:rv32
```

before `target extended-remote`.

3. If `load` fails, run:

```text
monitor ch32v006_flash_status
```

Interpretation:

- `fail=0x00` means the CH32V006 flash callback did not record an internal
  erase/write/load32 failure.
- A non-zero `fail` value points to the ESP32JTAG CH32V006 flash driver itself.
- `Error writing data to flash` with `fail=0x00` points more toward the GDB
  remote/register/readback boundary than the low-level flash row write.

4. Treat `compare-sections` with caution on this target until the remote
register-description issue is fixed.

## Future ESP32JTAG Firmware Fix Area

Do not change firmware just for this note. When ESP32JTAG firmware is next
modified, the likely fix area is the CH32V006 / RV32E target description and
register packet handling.

Things to inspect:

- the XML target description returned for CH32V006 (`riscv:rv32emc`)
- the remote `g` packet register count and size for RV32E
- whether the remote should return a target description that old WCH GDB 8.3 can
  parse
- whether Black Magic should suppress or adapt unsupported architecture strings
  for this GDB
- whether `compare-sections` is reading through the same address view that the
  CH32V006 flash driver writes and verifies internally

Relevant firmware-side files seen during this session:

```text
/nvme1t/work/esp32jtag_firmware/components/blackmagic_esp32/src/target/ch32v00x.c
/nvme1t/work/esp32jtag_firmware/docs/coreweaver_ch32v006_flash_stability_2026-06-27.md
```

## Current Practical Conclusion

The issue is not that the new board lacks CH32V006 debug connectivity. The board
can enter WCH SWIO debug mode and identify the chip.

The issue is also not that a different GDB was used for CH32V006 versus
CH32V305. Both used the same WCH RISC-V GDB 8.3.

The current weak point is the CH32V006-specific interaction between:

- old WCH GDB 8.3
- Black Magic remote target description / register packets
- RV32E / `rv32emc` target shape
- CH32V006 SWIO flash/readback path

Use `set architecture riscv:rv32` as the first workaround, and use
`monitor ch32v006_flash_status` to distinguish low-level flash-driver failure
from GDB remote/readback failure.
