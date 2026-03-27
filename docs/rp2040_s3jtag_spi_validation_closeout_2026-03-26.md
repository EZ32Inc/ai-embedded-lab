## RP2040 S3JTAG SPI Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Test plan: `tests/plans/rp2040_spi_loopback_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/spi_loopback_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage2.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 UART0 TX GPIO0` -> `S3JTAG UART1 RX GPIO7`
- `RP2040 UART0 RX GPIO1` -> `S3JTAG UART1 TX GPIO6`
- `RP2040 SPI0 TX GPIO3` -> `RP2040 SPI0 RX GPIO4`
- `RP2040 SPI0 SCK GPIO2` left as clock output only
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 SPI loopback golden firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 SPI loopback result observed through the `S3JTAG` internal Web UART bridge: PASS
- formal AEL test `tests/plans/rp2040_spi_loopback_with_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_21-13-25_rp2040_pico_s3jtag_uart_rp2040_spi_loopback_with_s3jtag`

Key evidence:
- SPI loopback firmware built successfully at `artifacts/build_rp2040_spi_loopback_s3jtag/pico_spi_loopback_s3jtag.elf`
- Formal run completed with `PASS: Run verified`
- Final formal run artifacts:
  - `runs/2026-03-26_21-13-25_rp2040_pico_s3jtag_uart_rp2040_spi_loopback_with_s3jtag/result.json`
  - `runs/2026-03-26_21-13-25_rp2040_pico_s3jtag_uart_rp2040_spi_loopback_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_21-13-25_rp2040_pico_s3jtag_uart_rp2040_spi_loopback_with_s3jtag/observe_uart.log`

Implementation details validated:
- SPI loopback uses `spi0`
- `GPIO2` is configured as `SPI0_SCK`
- `GPIO3` is configured as `SPI0_TX`
- `GPIO4` is configured as `SPI0_RX`
- loopback contract is direct local jumper `GPIO3 -> GPIO4`
- firmware sends fixed pattern `55 AA 3C C3`
- pass condition is exact `memcmp(pattern, rx)` match
- result is surfaced through repeated UART text rather than a GPIO signature

Diagnostic additions used during bring-up:
- Added boot/progress/result UART messages:
  - `AEL_READY RP2040 SPI BOOT`
  - `AEL_READY RP2040 SPI WAIT`
  - `AEL_READY RP2040 SPI XFER`
  - `AEL_READY RP2040 SPI PASS ...`
  - `AEL_READY RP2040 SPI FAIL ...`
- Added local `pico_sdk_import.cmake` so the firmware target can build in isolation like the other golden assets

What blocked SPI initially:
- The first failures were not pure SPI failures.
- The new SPI test depends on the same `S3JTAG` Web UART observation path used by the UART banner test.
- While UART observation was unstable, SPI could build and flash but still fail at `check_uart`, which made the SPI test look broken before the SPI firmware itself was actually disproven.

What changed before SPI finally passed:
1. `RP2040 UART banner` was rerun until it passed repeatedly on the same bench without extra GPIO diagnostics.
2. That established the `RP2040 -> ESP32-S3 -> Web UART -> AEL check` path as stable enough for dependent tests.
3. With the UART observation path stable, the unchanged SPI loopback test then passed on the next formal rerun.

This means the critical reusable lesson is:
- for any `RP2040 + S3JTAG` test that reports success through internal Web UART, stabilize UART first
- do not treat an early SPI `check_uart` failure as evidence that the SPI datapath itself is wrong until UART banner is known-good on the same bench state

Validated run sequence at closeout time:
- `rp2040_uart_banner_with_s3jtag` passed three consecutive times without invoking `test_uart_rxd_detect`
- after that, `rp2040_spi_loopback_with_s3jtag` passed on the next formal run

Associated commits:
- `9b91d03` `Add RP2040 S3JTAG SPI loopback test`
- `3e4f9df` `Add SPI loopback UART debug logging`

Conclusion:
- `RP2040 SPI0` local MOSI->MISO loopback is now validated through the `S3JTAG` SWD + internal Web UART bench path.
- The test is suitable as a `Rule-B Stage 2` exercised peripheral validation.
- The true dependency order for this bench is:
  - stable SWD/GDB
  - stable UART observe path
  - then SPI loopback validation
