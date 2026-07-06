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

Plain SWD scan did not detect this RP2040 reliably. The working path is to
enable connect-under-reset before scanning:

```sh
arm-none-eabi-gdb -q --nx --batch \
  artifacts/build_rp2040_pico/pico_blink.elf \
  -ex "set remotetimeout 60" \
  -ex "target extended-remote 192.168.4.1:4244" \
  -ex "monitor frequency 5000" \
  -ex "monitor connect_rst enable" \
  -ex "monitor swd_scan" \
  -ex "attach 1" \
  -ex "load" \
  -ex "compare-sections" \
  -ex "attach 1" \
  -ex "detach" \
  -ex "quit"
```

The flash verification matched all loaded sections:

```text
Section .boot2: matched
Section .text: matched
Section .rodata: matched
Section .binary_info: matched
Section .data: matched
```

The final `attach 1` before `detach` is intentional. It matches the
STM32F401/F411 BMDA post-load sequence that starts the target without requiring
a physical power cycle. Do not replace it with `monitor reset` or
`monitor reset run` for this CoreWeaver ARM/Cortex flow.
