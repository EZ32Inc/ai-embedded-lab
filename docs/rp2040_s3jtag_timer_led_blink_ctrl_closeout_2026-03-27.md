# RP2040 S3JTAG timer_led_blink_ctrl Closeout — 2026-03-27

## Summary

Created and validated a bidirectional LED blink control test for the RP2040 Pico using
the S3JTAG instrument. The test demonstrates timer-driven GPIO output and live mailbox
readback via SWD/GDB, including a live ON/OFF terminal monitor.

---

## What Was Done

### Firmware (`timer_led_blink_ctrl_s3jtag`)

- LED blinks on GPIO25 via a 10 ms repeating timer ISR (default 500 ms half-period, 1 Hz).
- Bidirectional AEL mailbox at `0x20041F00`:
  - **Firmware → PC** (`detail0`): `bit[0]` = led_state, `bits[15:1]` = toggle_count (15-bit wrap), `bits[31:16]` = active half-period in ms.
  - **PC → Firmware** (`cmd_period_ms` at `0x20041F10`): write desired half-period (50–5000 ms); firmware applies and clears on next tick.
- No wires required beyond SWDIO, SWCLK, GND.

### Test Plan (`rp2040_timer_led_blink_ctrl_s3jtag`)

- `test_kind: baremetal_mailbox`, `check_mode: detail0_increment`.
- Reads `detail0` twice 2 s apart; PASS if `toggle_count` incremented — confirms timer ISR is running.
- Test PASSED on 2026-03-27 with S3JTAG at 192.168.2.251, firmware `5a140ca`.

### Mailbox Adapter Extension (`check_mailbox_verify.py`)

- Added `detail0_increment` check mode alongside the existing `pass` mode.
- New helpers: `_extract_toggle_count()`, `_execute_detail0_increment()`.

### Live LED Terminal Monitor

- Python script polls the mailbox via GDB, prints `ON/OFF` line-by-line with `toggle_count`.
- Runs as a demo to show AEL can observe LED state in real time.

---

## Limitations

### GDB `attach` Halts the CPU

Every mailbox read requires:
1. GDB connects to BMDA on port 4242 (~2–3 s setup overhead).
2. `attach` halts both RP2040 cores.
3. Memory is read; `detach` resumes execution.

**Consequence:** the LED timer ISR cannot fire while the CPU is halted. With back-to-back
reads and no sleep between them, the LED is frozen almost continuously and does not blink
visibly. A 1 s sleep between reads is needed to let the firmware run freely so the physical
LED blinks at its nominal 1 Hz.

### No True Real-Time Sync

Because each GDB read introduces a 2–3 s interruption, the printed ON/OFF state is not
perfectly synchronised with the physical LED. The LED blinks freely between reads but is
frozen during the read window.

### Single GDB Session Limit

BMDA exposes a single-client GDB server. A crashed or stuck GDB session (e.g. from a GDB
MI experiment) blocks port 4242 until the S3JTAG is reset. Reset procedure:
- **Software**: POST to `/set_credentials` (triggers `esp_restart()`).
- **Hardware**: assert RTS on the USB-UART bridge (`/dev/ttyACM*`) to pull EN low, then release.

---

## Future Plan — BMP Semihosting

The correct long-term solution is **ARM semihosting** forwarded by BMDA:

1. Firmware executes `BKPT 0xAB` at each LED toggle (semihosting write call).
2. BMDA intercepts the semihosting event and forwards the payload over GDB RSP to the host.
3. AEL receives the event **at the exact moment of the LED toggle** — no polling, no CPU halt for memory reads.

**Benefits over GDB polling:**
- Zero disruption to the LED blink rate.
- Perfect synchronisation between the AEL-reported state and the physical LED.
- No 2–3 s GDB setup overhead per sample.
- Scales to any number of firmware events without adding GDB sessions.

This requires BMDA semihosting forwarding support to be enabled in the S3JTAG firmware,
which is planned as a future instrument capability.

---

## Instrument Used

| Field | Value |
|-------|-------|
| Instrument | s3jtag_rp2040_lab |
| IP | 192.168.2.251 |
| Firmware version | 0.1.0 |
| Git commit | 5a140ca |
| Build target | build_board_esp32s3_devkit |
| Board profile | esp32s3_devkit |
| Binary | esp32jtag_v0.1.0_20260327_124827_5a140ca_full.bin |
