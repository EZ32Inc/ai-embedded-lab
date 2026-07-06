# CoreWeaver RP2040 Pico GPIO25 Blinky Closeout

Date: 2026-06-28

## Target

- Board: Raspberry Pi Pico / RP2040 on CoreWeaver channel 2
- LED: Pico onboard LED on GPIO25
- Debug path: CoreWeaver ESP32-S3 S3JTAG8CH channel 2
- GDB endpoint: `192.168.4.1:4244`

## Firmware

Firmware path:

```text
firmware/targets/rp2040_pico
```

The program toggles GPIO25 every 500 ms:

```c
const uint led_pin = 25;
gpio_init(led_pin);
gpio_set_dir(led_pin, GPIO_OUT);

while (true) {
    led = !led;
    gpio_put(led_pin, led);
    sleep_ms(500);
}
```

The previous GPIO16-19 fast logic-analyzer signature code was removed from this
target so the target is now a direct visual LED blink test.

## Build

```sh
cmake -S firmware/targets/rp2040_pico \
  -B artifacts/build_rp2040_pico \
  -DPICO_SDK_PATH=/nvme1t/github/pico-sdk

cmake --build artifacts/build_rp2040_pico -j4
```

Output ELF:

```text
artifacts/build_rp2040_pico/pico_blink.elf
```

## Flash

Plain SWD scan at the default speed did not detect this RP2040 reliably. The
working path is to lower the requested SWD speed before scanning, then use the
same post-load resume shape as the March 2026 RP2040 S3JTAG golden runs:

```sh
arm-none-eabi-gdb -q --nx --batch \
  artifacts/build_rp2040_pico/pico_blink.elf \
  -ex "set remotetimeout 15" \
  -ex "target extended-remote 192.168.4.1:4244" \
  -ex "monitor frequency 1000" \
  -ex "monitor swd_scan" \
  -ex "attach 1" \
  -ex "load" \
  -ex "monitor reset run" \
  -ex "continue" \
  -ex "detach" \
  -ex "quit"
```

The validated run reports `Remote failure reply: E01` / `FF` after the
post-load reset and continue. This matches the older RP2040 S3JTAG golden-run
shape when reset is not wired, and the target starts running immediately after
GDB detaches.

Do not use the STM32-style final `attach 1` followed by `detach` for this RP2040
path, and do not insert `compare-sections` between `load` and the post-load
resume sequence. Those variants can leave the RP2040 halted until the next
target power cycle even though the flash contents are valid.
