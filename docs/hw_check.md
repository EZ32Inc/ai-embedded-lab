# USB Hardware Check

`ael hw-check` is the normalized USB-side board health check for directly attached ESP32-class boards.

Example:

```bash
python3 -m ael hw-check --board esp32c3_devkit --port /dev/ttyACM0
python3 -m ael hw-check --board esp32c3_devkit --port /dev/ttyACM0 --expect-pattern AEL_DUT_READY
```

What it checks:

- serial device exists
- serial device stays present across multiple samples
- `esptool` can identify the chip on that port
- best-effort live UART capture, with reset-and-read fallback if needed
- optional expected UART token is present

Pass criteria:

- port stable
- chip probe succeeds
- boot log is advisory by default
- if `--expect-pattern` is used, boot capture must succeed and that token must appear in the captured boot sample

This is intended for requests like:

- "I have connected the board to USB port, please check if HW is working"
