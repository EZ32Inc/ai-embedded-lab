## RP2040 S3JTAG UART Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Pack: `packs/uart_rp2040_s3jtag.json`
- Test plan: `tests/plans/rp2040_uart_banner_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/uart_banner_s3jtag/firmware`
- Supporting firmware-side diagnostic hook: `test_uart_rxd_detect` on the `esp32s3_devkit` board profile

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 UART0 TX GPIO0` -> `S3JTAG UART1 RX GPIO7`
- `RP2040 UART0 RX GPIO1` -> `S3JTAG UART1 TX GPIO6`
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 UART golden firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 UART banner observed through the `S3JTAG` internal Web UART bridge: PASS
- formal AEL pack `packs/uart_rp2040_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag`

Key evidence:
- RP2040 UART golden firmware built successfully at `artifacts/build_rp2040_uart_banner_s3jtag/pico_uart_banner_s3jtag.elf`
- ESP32-S3 USB console confirmed the UART driver was receiving the expected banner repeatedly:

```text
I (...) uart_websocket: From UART: len=23, data: AEL_READY RP2040 UART
```

- A direct websocket client against `wss://192.168.4.1/ws` received repeated banner frames:

```text
recv 'AEL_READY RP2040 UART\r\n'
recv 'AEL_READY RP2040 UART\r\n'
```

- The exact AEL helper `_capture_via_esp32jtag_web_uart('https://192.168.4.1:443', 6.0, 0.0)` returned banner bytes successfully.
- Final formal run artifacts:
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/result.json`
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/uart_observe.json`

What failed first and why:
- The ESP32-S3 firmware had drifted to the wrong default AP naming convention for this bench (`esp-openocd`), which made recovery and connection assumptions inconsistent with the saved host profile.
- On fresh boards, first-boot NVS initialization seeded `pc_cfg=0`, which prevented the `gdb_server` task from starting and made `192.168.4.1:4242` look dead until the storage default bug was fixed.
- After the generic devkit baseline was restored, the UART pack still failed in multiple distinct ways over time:
  - `preflight` could not reach `https://192.168.4.1:443` because `_tcp_ping()` was parsing scheme-bearing endpoints incorrectly
  - websocket handshake sometimes timed out because the client timeout was too short
  - later runs still showed `bytes=0`, which at first looked like missing UART traffic but was actually a moving bench-state problem while the board and wiring were being recovered
- A separate bench interruption pulled the ESP32-S3 into repeated brownout and `DOWNLOAD(USB/UART0)` boot mode, which temporarily removed the AP entirely and made UART investigation impossible until power and wiring were stabilized.

Evidence that separated false leads from the real path:
- RP2040 was never silent. The golden firmware prints `AEL_READY RP2040 UART` once after boot and again every second after that, so a totally empty capture should be treated as a transport problem, not a target-firmware problem.
- Direct GPIO sampling on `GPIO7` with the firmware-side `test_uart_rxd_detect` hook proved the RP2040 TX waveform was physically reaching the ESP32-S3 RX pin:

```json
{"test":"test_uart_rxd_detect","result":"pass","pin":7,"state":"toggle","samples":9401,"high":9355,"low":46,"transitions":42,"estimated_hz":84}
```

- ESP32-S3 USB console then proved the UART driver was decoding real bytes, which eliminated wiring and baud mismatch as the primary blocker.
- A manual websocket client finally proved the network-side bridge was also working, which narrowed the remaining suspicion back to pack timing and transient bench state rather than a fundamental firmware bridge defect.
- Once the board was stable and the bench wiring was corrected, the unchanged formal pack moved straight to `PASS`.

Last-known-good recovery steps:
- Rejoin the host to the instrument AP if needed:
  - `nmcli connection up esp32jtag_0F91 ifname wlx90de80a53084`
- Confirm control path health before chasing UART:
  - `arm-none-eabi-gdb -q -ex 'target extended-remote 192.168.4.1:4242' -ex 'monitor swd_scan' -ex 'quit'`
- If UART looks empty, separate the chain in this order:
  1. prove RP2040 TX is reaching `GPIO7` with `test_uart_rxd_detect`
  2. prove ESP32-S3 UART driver sees bytes on USB console
  3. prove `wss://192.168.4.1/ws` yields banner frames with a direct client
  4. only then retry the formal AEL pack
- If the ESP32-S3 falls into ROM download mode or brownout loop, recover power and boot state before doing any AEL-side debugging.

AEL-side fixes required for the formal pack path:
- `610a3ab` `Unblock S3JTAG UART preflight and websocket capture`

Related firmware-side fixes and diagnostics:
- `6af4936` `Fix first-boot gdb server defaults`
- `5a140ca` `Add UART RX GPIO diagnostic hook`

Conclusion:
- The `S3JTAG` pattern is now validated for `RP2040` as a combined SWD flash + internal Web UART bridge instrument path.
- This path is now proven both through ad hoc live diagnostics and through a formal AEL pack run.
- The decisive debugging sequence for this bench was layered:
  - signal reaches the RX pin
  - UART driver decodes bytes
  - websocket bridge emits frames
  - formal AEL pack captures the expected banner
