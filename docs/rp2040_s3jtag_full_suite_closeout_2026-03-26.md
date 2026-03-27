## RP2040 S3JTAG Full Suite Closeout

Date: 2026-03-26

Scope:
- Pack: `packs/rp2040_s3jtag_full.json`
- Pack run: `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag`
- Board profiles:
  - `configs/boards/rp2040_pico_s3jtag.yaml`
  - `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Validated ESP32-S3 firmware repo: `/nvme1t/work/esp32jtag_firmware`
- Validated ESP32-S3 firmware commit: `5a140cab59306f687e6affd4808df5be0ec8a779` (`5a140ca Add UART RX GPIO diagnostic hook`)

Bench shape validated:
- `S3JTAG GPIO4` -> `RP2040 SWCLK`
- `S3JTAG GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GPIO7` <- `RP2040 GPIO0/UART0_TX`
- `S3JTAG GPIO6` -> `RP2040 GPIO1/UART0_RX`
- `S3JTAG GPIO15 TARGETIN` <- `RP2040 GPIO18`
- local SPI loopback: `RP2040 GPIO3/SPI0_TX` -> `RP2040 GPIO4/SPI0_RX`
- local GPIO IRQ loopback: `RP2040 GPIO16` -> `RP2040 GPIO17`
- common `GND`

Result summary:
- formal pack `packs/rp2040_s3jtag_full.json`: PASS
- pack result file: `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag/pack_result.json`
- pack report: `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag/pack_report.html`

Per-test PASS list:
- `rp2040_minimal_runtime_mailbox_s3jtag`
- `rp2040_internal_temp_mailbox_s3jtag`
- `rp2040_timer_mailbox_s3jtag`
- `rp2040_gpio_level_low_with_s3jtag`
- `rp2040_gpio_level_high_with_s3jtag`
- `rp2040_gpio_signature_100hz_with_s3jtag`
- `rp2040_gpio_signature_with_s3jtag`
- `rp2040_pwm_capture_with_s3jtag`
- `rp2040_gpio_interrupt_loopback_with_s3jtag`
- `rp2040_uart_rxd_detect_with_s3jtag`
- `rp2040_uart_banner_with_s3jtag`
- `rp2040_spi_loopback_with_s3jtag`

Successful run ids:
- `2026-03-26_22-24-16_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag`
- `2026-03-26_22-24-25_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag`
- `2026-03-26_22-24-33_rp2040_pico_s3jtag_rp2040_timer_mailbox_s3jtag`
- `2026-03-26_22-24-43_rp2040_pico_s3jtag_rp2040_gpio_level_low_with_s3jtag`
- `2026-03-26_22-25-00_rp2040_pico_s3jtag_rp2040_gpio_level_high_with_s3jtag`
- `2026-03-26_22-25-32_rp2040_pico_s3jtag_rp2040_gpio_signature_100hz_with_s3jtag`
- `2026-03-26_22-26-02_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag`
- `2026-03-26_22-26-34_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag`
- `2026-03-26_22-27-04_rp2040_pico_s3jtag_rp2040_gpio_interrupt_loopback_with_s3jtag`
- `2026-03-26_22-27-19_rp2040_pico_s3jtag_rp2040_uart_rxd_detect_with_s3jtag`
- `2026-03-26_22-27-38_rp2040_pico_s3jtag_rp2040_uart_banner_with_s3jtag`
- `2026-03-26_22-27-51_rp2040_pico_s3jtag_rp2040_spi_loopback_with_s3jtag`

Key evidence:
- Pack-level evidence:
  - `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag/pack_result.json`
  - `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag/pack_plan.json`
  - `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag/pack_meta.json`
- Representative stage evidence:
  - mailbox baseline: `runs/2026-03-26_22-24-16_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag/artifacts/mailbox_verify.json`
  - Stage 1 internal self-test: `runs/2026-03-26_22-24-25_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag/artifacts/evidence.json`
  - TARGETIN high/low/toggle: `runs/2026-03-26_22-25-00_rp2040_pico_s3jtag_rp2040_gpio_level_high_with_s3jtag/artifacts/verify_result.json`
  - UART text path: `runs/2026-03-26_22-27-38_rp2040_pico_s3jtag_rp2040_uart_banner_with_s3jtag/artifacts/verify_result.json`
  - SPI loopback path: `runs/2026-03-26_22-27-51_rp2040_pico_s3jtag_rp2040_spi_loopback_with_s3jtag/artifacts/verify_result.json`

What mattered during validation:
- The `TARGETIN` family had to be retargeted from `RP2040 GPIO16` to `RP2040 GPIO18` so the GPIO level/signature tests and PWM capture could share one fixed wiring contract.
- With that retarget complete, the same bench wiring supported all 12 tests in one formal full-pack run.
- The validated `esp32jtag_firmware` revision for this suite is the already-committed `5a140ca`; the firmware repo had no additional source changes pending during this closeout, only untracked build directories.

Validated fixed-wiring contract for the full suite:
- `SWDIO -> P3.SWDIO`
- `SWCLK -> P3.SWCLK`
- `GND -> GND`
- `GPIO0 -> GPIO7`
- `GPIO1 -> GPIO6`
- `GPIO3 -> GPIO4`
- `GPIO16 -> GPIO17`
- `GPIO18 -> GPIO15/TARGETIN`

Conclusion:
- `packs/rp2040_s3jtag_full.json` is now validated as a real fixed-wiring 12-test suite on the current RP2040 + S3JTAG bench.
- The suite covers Stage 0 runtime gate, Stage 1 no-wire internal self-tests, TARGETIN signal tests, UART raw/text paths, GPIO interrupt loopback, and SPI loopback.
- The validated S3JTAG firmware revision tied to this suite result is `5a140ca`.
