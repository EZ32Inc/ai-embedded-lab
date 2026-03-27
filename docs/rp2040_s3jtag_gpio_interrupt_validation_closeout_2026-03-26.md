## RP2040 S3JTAG GPIO Interrupt Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Test plan: `tests/plans/rp2040_gpio_interrupt_loopback_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/firmware`
- Pack coverage: `packs/rp2040_s3jtag_stage2.json`, `packs/rp2040_s3jtag_full.json`

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 GPIO16` -> `RP2040 GPIO17`
- `RP2040 UART0 TX GPIO0` -> `S3JTAG UART1 RX GPIO7`
- `RP2040 UART0 RX GPIO1` -> `S3JTAG UART1 TX GPIO6`
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 GPIO interrupt loopback firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 local `GPIO16 -> GPIO17` interrupt burst and count: PASS
- formal AEL test `tests/plans/rp2040_gpio_interrupt_loopback_with_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_21-51-08_rp2040_pico_s3jtag_uart_rp2040_gpio_interrupt_loopback_with_s3jtag`

Key evidence:
- Final formal run artifacts:
  - `runs/2026-03-26_21-51-08_rp2040_pico_s3jtag_uart_rp2040_gpio_interrupt_loopback_with_s3jtag/result.json`
  - `runs/2026-03-26_21-51-08_rp2040_pico_s3jtag_uart_rp2040_gpio_interrupt_loopback_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_21-51-08_rp2040_pico_s3jtag_uart_rp2040_gpio_interrupt_loopback_with_s3jtag/artifacts/evidence.json`
- This test passed using the bounded Web UART PASS message:
  - `AEL_READY RP2040 GPIO_IRQ PASS count=100 target=100`

Implementation details validated:
- `GPIO16` is the pulse output.
- `GPIO17` is configured as a rising-edge interrupt input.
- The firmware emits a fixed burst of `100` pulses.
- The pass condition is internal to the DUT:
  - interrupt count must equal the target pulse count
- Result reporting uses the already-validated S3JTAG Web UART bridge.

What mattered during validation:
- Earlier attempts failed while the UART path itself was unstable.
- After formalizing and passing `rp2040_uart_rxd_detect_with_s3jtag`, and then revalidating `rp2040_uart_banner_with_s3jtag`, the exact same GPIO interrupt loopback test passed without changing the firmware logic again.
- This shows the GPIO interrupt test logic was sound; the earlier failures were dominated by upstream UART-observe instability rather than the interrupt loopback itself.

Why this test matters:
- It extends `Stage 2` beyond simple GPIO level/frequency observation into an exercised interrupt feature path.
- It validates a local wired loopback contract on the RP2040 itself, not just a signal measured at the instrument.
- It gives a reusable way to prove:
  - GPIO output activity
  - GPIO input reception
  - interrupt edge handling
  - bounded DUT-side pass/fail logic

Associated assets added:
- `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/docs.md`
- `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/manifest.yaml`
- `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/firmware/CMakeLists.txt`
- `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/firmware/main.c`
- `assets_golden/duts/rp2040_pico/gpio_interrupt_loopback_s3jtag/firmware/pico_sdk_import.cmake`
- `tests/plans/rp2040_gpio_interrupt_loopback_with_s3jtag.json`

Conclusion:
- `RP2040 GPIO16 -> GPIO17` interrupt loopback is now validated through the `S3JTAG` SWD + internal Web UART bench path.
- This test is suitable as a `Rule-B Stage 2` exercised peripheral validation.
- The validated wiring contract is explicit and minimal:
  - `GPIO16 -> GPIO17`
  - plus the already-required SWD/UART/GND connections to `S3JTAG`
