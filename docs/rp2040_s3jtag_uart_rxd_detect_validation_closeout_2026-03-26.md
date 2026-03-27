## RP2040 S3JTAG UART RX Raw Detect Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Test plan: `tests/plans/rp2040_uart_rxd_detect_with_s3jtag.json`
- Golden firmware reused: `assets_golden/duts/rp2040_pico/uart_banner_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage2.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 UART0 TX GPIO0` -> `S3JTAG UART1 RX GPIO7`
- `RP2040 UART0 RX GPIO1` -> `S3JTAG UART1 TX GPIO6`
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 UART banner firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- S3JTAG raw `GPIO7` detect on the UART RX path: PASS
- formal AEL test `tests/plans/rp2040_uart_rxd_detect_with_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_21-47-31_rp2040_pico_s3jtag_uart_rp2040_uart_rxd_detect_with_s3jtag`
- follow-on UART websocket/banner test after raw detect: PASS
- successful follow-on UART run id: `2026-03-26_21-47-56_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag`

Key evidence:
- Final raw-detect verification reported:
  - `state=toggle`
  - `transitions=42`
  - `estimated_hz=83`
- Final raw-detect run artifacts:
  - `runs/2026-03-26_21-47-31_rp2040_pico_s3jtag_uart_rp2040_uart_rxd_detect_with_s3jtag/result.json`
  - `runs/2026-03-26_21-47-31_rp2040_pico_s3jtag_uart_rp2040_uart_rxd_detect_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_21-47-31_rp2040_pico_s3jtag_uart_rp2040_uart_rxd_detect_with_s3jtag/artifacts/evidence.json`
- Follow-on UART banner run artifacts:
  - `runs/2026-03-26_21-47-56_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/result.json`
  - `runs/2026-03-26_21-47-56_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/artifacts/verify_result.json`

Implementation details validated:
- AEL formal GPIO observation now supports web-test-backed signal checks for:
  - `TARGETIN`
  - `UART_RXD`
- The `esp32jtag` capture wrapper now preserves `uart_rxd_result` through the native interface path.
- The formal raw-detect test intentionally reuses the proven `uart_banner_s3jtag` firmware so the only new verification variable is the `GPIO7` signal observation path.

What mattered during validation:
- The first formal raw-detect attempt showed `Verify: UART_RXD detect OK`, but still failed final verification because the new `uart_rxd_result` payload was not being forwarded through the interface layer.
- Two code-path fixes were required to formalize this test correctly:
  - `ael/adapters/observe_gpio_pin.py`
    - add formal `UART_RXD` / `GPIO7` support via the existing S3JTAG web test API `test_uart_rxd_detect`
  - `ael/instruments/interfaces/esp32jtag.py`
    - forward `uart_rxd_result` in the `capture_signature` success mapper
  - `ael/adapter_registry.py`
    - accept `uart_rxd_result` in the same final verdict path already used for `targetin_result`
- Once those were in place, the raw-detect formal test passed immediately, and the subsequent full `UART banner` test also passed.

Why this new test matters:
- It separates two different failure classes that previously both looked like `UART bytes=0`:
  - no physical signal arriving at `GPIO7`
  - signal present at `GPIO7`, but websocket / text capture failing later
- This makes it a useful `Stage 2` pre-check before `rp2040_uart_banner_with_s3jtag` and other UART-dependent tests such as `rp2040_spi_loopback_with_s3jtag`.

Associated assets added:
- `tests/plans/rp2040_uart_rxd_detect_with_s3jtag.json`
- `tests/test_observe_gpio_pin.py`
- `ael/adapters/observe_gpio_pin.py`
- `ael/adapter_registry.py`
- `ael/instruments/interfaces/esp32jtag.py`
- `packs/rp2040_s3jtag_stage2.json`
- `packs/rp2040_s3jtag_full.json`

Conclusion:
- `RP2040 UART0_TX -> S3JTAG GPIO7` now has a formal raw-detect validation path in AEL.
- The new test is suitable as a `Rule-B Stage 2` exercised signal-path check ahead of higher-level UART text verification.
- On this bench state, the successful sequence was:
  - formal `rp2040_uart_rxd_detect_with_s3jtag`: PASS
  - formal `rp2040_uart_banner_with_s3jtag`: PASS
