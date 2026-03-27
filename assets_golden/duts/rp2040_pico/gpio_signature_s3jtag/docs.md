# RP2040 Pico GPIO Signature Asset For S3JTAG

This golden DUT test asset builds a Pico SDK firmware that is intended for the `S3JTAG` path.

Default DUT pin:
- GPIO18: toggle 1 kHz, nominal 50% duty

Expected bench wiring:
- RP2040 SWDIO -> S3JTAG P3.SWDIO
- RP2040 SWCLK -> S3JTAG P3.SWCLK
- RP2040 GPIO18 -> S3JTAG TARGETIN (GPIO15)
- GND -> GND

Notes:
- This asset is intentionally single-channel. It is designed for `TARGETIN` validation, not FPGA logic capture.
- RP2040 reset is not required on this path.
