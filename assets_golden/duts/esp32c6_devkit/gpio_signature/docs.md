# ESP32-C6 GPIO Signature Asset

This golden DUT test asset builds an ESP-IDF firmware that emits a stable 4-channel GPIO signature for external instrument verification.

Default DUT pins:
- X1 (GPIO4): toggle 1kHz
- X2 (GPIO5): toggle 2kHz
- X3 (GPIO6): steady HIGH
- X4 (GPIO7): steady LOW

The firmware prints `AEL_DUT_READY` on UART after setup.
