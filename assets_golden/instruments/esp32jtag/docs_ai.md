ESP32JTAG instrument (BMDP-based).

Capabilities:
- debug.swd via GDB server (default 192.168.4.1:4242)
- observe.logic via HTTPS API (default 192.168.4.1:443)
- observe.uart via USB CDC (/dev/ttyACM*)

Notes:
- Requires Wi-Fi AP connection or Ethernet, depending on board setup.
- Some targets need power cycle after flashing if they appear hung.
