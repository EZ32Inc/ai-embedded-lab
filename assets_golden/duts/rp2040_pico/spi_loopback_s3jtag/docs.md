# spi_loopback_s3jtag

RP2040 SPI loopback asset for the S3JTAG bench.

- flash/debug path: `S3JTAG` over SWD
- UART observe path: S3JTAG internal ESP32-S3 Web UART bridge
- required bench wire: `GPIO3/SPI0_TX (MOSI)` -> `GPIO4/SPI0_RX (MISO)`
- expected bounded result: repeated `AEL_READY RP2040 SPI PASS ...`
