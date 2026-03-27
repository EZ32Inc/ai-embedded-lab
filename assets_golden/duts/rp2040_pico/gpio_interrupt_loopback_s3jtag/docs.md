# gpio_interrupt_loopback_s3jtag

RP2040 GPIO interrupt loopback asset for the S3JTAG bench.

- flash/debug path: `S3JTAG` over SWD
- UART observe path: S3JTAG internal ESP32-S3 Web UART bridge
- required bench wire: `GPIO16` -> `GPIO17`
- expected bounded result: repeated `AEL_READY RP2040 GPIO_IRQ PASS ...`
