## RP2040 Internal Temperature Mailbox Test (S3JTAG)

No-wire Stage 1 self-test for `RP2040 + S3JTAG`.

Purpose:
- validate that the RP2040 internal temperature sensor ADC path is alive
- report PASS/FAIL through the AEL mailbox
- avoid any dependency on UART or TARGETIN wiring

Validated contract:
- SWD flash and mailbox read over `S3JTAG`
- no extra bench wiring beyond SWD and GND
