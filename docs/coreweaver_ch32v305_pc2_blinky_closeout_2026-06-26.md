# CoreWeaver CH32V305 PC2 Blinky Closeout

Date: 2026-06-26

## Scope

Bring up the board-mounted CH32V305 on CoreWeaver channel 5 using the S3JTAG8CH
Black Magic GDB remote.

Connection:

- CoreWeaver host: `192.168.4.1`
- S3JTAG8CH channel: `5`
- GDB port: `4247`
- Target detected by Black Magic: `CH32V (unknown variant) QingKe V4`
- LED net: `PC2`

## Firmware

Added:

```text
firmware/targets/ch32v305_pc2_blinky/
```

The firmware is a minimal CH32V305 bare-metal program based on the existing
CH32V305 target skeleton:

- keeps the WCH CH32V30x startup, linker script, and headers
- builds with `rv32imafcxw` / `ilp32f`
- enables GPIOC through `RCC->APB2PCENR`
- configures `PC2` as push-pull output
- toggles `PC2` every 500 ms

## Build

Command:

```bash
make -C firmware/targets/ch32v305_pc2_blinky clean all
```

Result: build passed.

## Flash And Verify

Command:

```bash
/nvme1t/wch-riscv-gcc/bin/riscv-none-embed-gdb -q --nx --batch \
  -ex 'target extended-remote 192.168.4.1:4247' \
  -ex 'monitor frequency 100000' \
  -ex 'monitor swd_scan' \
  -ex 'attach 1' \
  -ex 'file firmware/targets/ch32v305_pc2_blinky/ch32v305_pc2_blinky.elf' \
  -ex 'load' \
  -ex 'compare-sections' \
  -ex 'monitor reset run' \
  -ex 'detach' \
  -ex 'quit'
```

Result:

- `monitor swd_scan` found `CH32V (unknown variant) QingKe V4`
- `load` completed
- `compare-sections` matched `.init`, `.vector`, and `.text`
- `monitor reset run` issued

Note: GDB printed an XML target description warning for `riscv:rv32imafc`, but
program load and section comparison completed successfully.

## Visual Validation

Operator confirmed the CH32V305 `PC2` LED is blinking.

Conclusion: CoreWeaver channel 5 programming and CH32V305 PC2 GPIO output are
validated.
