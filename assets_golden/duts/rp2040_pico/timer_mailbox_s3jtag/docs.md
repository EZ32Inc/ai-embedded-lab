## RP2040 Timer Mailbox Test (S3JTAG)

No-wire Stage 1 self-test for `RP2040 + S3JTAG`.

Purpose:
- validate that the RP2040 timer callback path is alive
- report PASS/FAIL through the AEL mailbox
- avoid any dependency on UART or TARGETIN wiring

Validated contract:
- SWD flash and mailbox read over `S3JTAG`
- no extra bench wiring beyond SWD and GND
