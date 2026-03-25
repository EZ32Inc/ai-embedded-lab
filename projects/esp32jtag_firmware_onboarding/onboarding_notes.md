# ESP32JTAG Firmware Onboarding — Session Notes

## 2026-03-24

### Hardware confirmed
- Two physical ESP32JTAG boards:
  - `.111` — existing instrument (esp32jtag_g431_bench), used in production
  - `/dev/ttyACM0` serial=3C:DC:75:5A:9A:FC, gets IP .62 — this brownfield project board

### AEL agent error to note
During boot log capture, an RTS/DTR reset sequence was attempted via pyserial.
This is INCORRECT for this hardware (no bridge chip, native USB only).
The reset happened to work because esptool's USB JTAG stub may have responded,
but this approach is unreliable and must not be used in production AEL flows.
Correct approach: either wait for periodic log output, or request user to
manually press RESET.

### Boot log captured
Full boot sequence logged. Key timings:
- t=0ms:    ROM bootloader
- t=775ms:  app_main() starts
- t=1815ms: FPGA configured OK
- t=4395ms: WiFi connected, IP assigned (192.168.2.62)
- t=4415ms: [APP] Free memory → fully ready
- t=4415ms+: heartbeat every 3000ms

### Firmware state at onboarding
- STA mode, connects to BELL567
- Port C = SWD/JTAG active
- USB DAP disabled (NVS setting)
- GDB server on port 4242
