# rp2040_pico

Wiring expectations:
- SWD via ESP32JTAG P3
- Verify pin uses LA CH1 (P0.0)

Notes:
- Uses firmware in `firmware/` (symlink to repo root firmware).

S3JTAG variant:
- Dedicated golden asset: `assets_golden/duts/rp2040_pico/gpio_signature_s3jtag/`
- SWD via S3JTAG P3
- Verify pin uses `TARGETIN` on S3JTAG GPIO15
- Golden firmware drives RP2040 GPIO16 at 1 kHz
- Dedicated minimal-runtime mailbox asset: `assets_golden/duts/rp2040_pico/minimal_runtime_mailbox_s3jtag/`
