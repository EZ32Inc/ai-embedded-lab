# CoreWeaver STM32H503 PC13 Blinky Closeout

Date: 2026-06-26

## Scope

Bring up the board-mounted STM32H503 on CoreWeaver channel 4 using the
S3JTAG8CH Black Magic GDB remote.

Connection:

- CoreWeaver host: `192.168.4.1`
- S3JTAG8CH channel: `4`
- GDB port: `4246`
- Target detected by Black Magic: `STM32H5 M33`
- LED net: `PC13`

## Firmware

Added:

```text
firmware/targets/stm32h503_pc13_blinky/
```

The firmware is a minimal Cortex-M33 bare-metal program:

- vector table and reset handler in `startup.c`
- STM32H503 flash/RAM linker script in `stm32h503.ld`
- no HAL dependency
- enables GPIOC through `RCC_AHB2ENR`
- configures `PC13` as push-pull output
- continuously toggles `PC13`

## Build

Command:

```bash
make -C firmware/targets/stm32h503_pc13_blinky clean all
```

Result: build passed.

## Flash And Verify

Command:

```bash
arm-none-eabi-gdb -q --nx --batch \
  -ex 'target extended-remote 192.168.4.1:4246' \
  -ex 'monitor frequency 100000' \
  -ex 'monitor swd_scan' \
  -ex 'attach 1' \
  -ex 'file firmware/targets/stm32h503_pc13_blinky/build/stm32h503_pc13_blinky.elf' \
  -ex 'load' \
  -ex 'compare-sections' \
  -ex 'attach 1' \
  -ex 'detach' \
  -ex 'quit'
```

Result:

- `monitor swd_scan` found `STM32H5 M33`
- `load` completed
- `compare-sections` matched `.isr_vector`
- `compare-sections` matched `.text`
- second `attach 1` then `detach` issued so the target starts without a power
  cycle

## Visual Validation

Operator confirmed the STM32H503 `PC13` LED is blinking.

Conclusion: CoreWeaver channel 4 SWD programming and STM32H503 PC13 GPIO output
are validated.
