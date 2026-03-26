# RP2040 Pico Minimal Runtime Mailbox via S3JTAG

Purpose:
- Provide a no-extra-wiring runtime baseline for `rp2040_pico_s3jtag`.
- Verify SWD flash + mailbox read without depending on `TARGETIN`.

Behavior:
- Initializes the AEL mailbox at `0x20041F00`.
- Marks `RUNNING`, then `PASS`.
- Increments `detail0` in the idle loop as a heartbeat.
- Toggles the onboard LED as a visual-only liveness hint.
