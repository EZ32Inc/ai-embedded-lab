# CoreWeaver RP2354 GPIO25 Blinky Closeout

Date: 2026-06-26

## Scope

Bring up the board-mounted RP2354 on CoreWeaver channel 6 using the S3JTAG8CH
Black Magic GDB remote.

Connection:

- CoreWeaver host: `192.168.4.1`
- S3JTAG8CH channel: `6`
- GDB port: `4248`
- Target detected by Black Magic: `RP2350 M33`; `RP2350 M33`
- LED net: `GPIO25`

The board uses RP2354, with on-chip flash. For this GPIO blinky firmware, Pico
SDK `pico2` / RP2350 Cortex-M33 support is sufficient.

## Firmware

Added:

```text
firmware/targets/rp2354_coreweaver_blinky/
```

The firmware is a minimal Pico SDK program:

- builds for `PICO_BOARD=pico2`
- disables USB and UART stdio
- configures GPIO25 as output
- toggles GPIO25 every 250 ms

## Build

Commands:

```bash
cmake -S firmware/targets/rp2354_coreweaver_blinky \
  -B artifacts/build_rp2354_coreweaver_blinky \
  -DPICO_SDK_PATH=/nvme1t/github/pico-sdk \
  -DCMAKE_BUILD_TYPE=Release
cmake --build artifacts/build_rp2354_coreweaver_blinky -j
```

Result: build passed.

## Flash And Verify

Command:

```bash
arm-none-eabi-gdb -q --nx --batch \
  -ex 'target extended-remote 192.168.4.1:4248' \
  -ex 'monitor frequency 100000' \
  -ex 'monitor swd_scan' \
  -ex 'attach 1' \
  -ex 'file artifacts/build_rp2354_coreweaver_blinky/rp2354_coreweaver_blinky.elf' \
  -ex 'load' \
  -ex 'compare-sections' \
  -ex 'monitor reset run' \
  -ex 'detach' \
  -ex 'quit'
```

Result:

- `monitor swd_scan` found both RP2350 M33 cores
- `load` completed to flash at `0x10000000`
- `compare-sections` matched `.text`, `.rodata`, `.ARM.exidx`, `.binary_info`,
  `.data`, and `.flash_end`
- `monitor reset run` issued

## Visual Validation

Operator confirmed the RP2354 GPIO25 LED is blinking.

Conclusion: CoreWeaver channel 6 SWD programming and RP2354 GPIO25 output are
validated.
