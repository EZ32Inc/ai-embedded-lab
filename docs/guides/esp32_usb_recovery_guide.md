# ESP32 USB Recovery Guide
# Diagnosing and recovering from USB/console problems in AEL

This guide covers the decision tree for when:
- `/dev/ttyACM*` is not found
- observe_uart gets zero bytes
- Flash fails with "no serial port"
- The board seems unresponsive after a failed run

It distinguishes between AEL/software problems (fixable without touching hardware)
and genuine hardware/firmware problems (requiring physical intervention).

---

## Quick Diagnosis Tree

```
observe_uart fails / no serial port
         │
         ▼
  Is /dev/ttyACM* present?
  (ls /dev/ttyACM* /dev/ttyUSB*)
         │
    ┌────┴────┐
   YES       NO
    │         │
    ▼         ▼
  Go to    Is board powered?
  Section A  ┌────┴────┐
            YES       NO
             │         │
             ▼         ▼
         What USB    Plug in USB / check cable
         class?      Then retry from top
          │
     ┌────┴────┐
     │         │
  Class A   Class B
  (dual)    (native-only)
     │         │
  Section B  Section C
```

---

## Section A — Port present but observe_uart fails

The port exists (`/dev/ttyACM*` is there), but AEL reports no data or wrong data.

### A1. AEL bug (software-only, no hardware action)

**Symptom**: `bytes_read=0`, `stuck_download_suspected` hint, but board is running normally.

**Check**: Can you read from the port manually?
```bash
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
start = time.time()
while time.time() - start < 5:
    d = s.read(4096)
    if d: print(d.decode('utf-8', errors='replace'), end='')
"
```

If this prints boot log → AEL config is wrong. Check:
- `baud` in test plan set to `null` and AEL ≥ 2026-03-24 (baud=null fix applied)
- `port` in test plan matches actual `/dev/tty*` device
- `usb_serial` in board config matches actual device

**Symptom**: `missing_expect` — data received but patterns not matched.

Check:
```bash
# Find latest run's raw uart log
ls -t runs/*/observe_uart.log | head -1 | xargs cat
```
Compare against your `expect_patterns`. See `observe_uart_boot_pattern_guide.md`.

### A2. Permission denied

**Symptom**: `UART permission check failed`, `permission denied`

Fix (one-time, requires re-login):
```bash
sudo usermod -a -G dialout $USER
# Log out and back in, or:
newgrp dialout
```

### A3. Port locked by another process

**Symptom**: `failed to open UART port`, port exists but can't open.

Check:
```bash
fuser /dev/ttyACM0          # shows PID holding the port
lsof /dev/ttyACM0           # more detail
```

Fix: kill the process (`kill <PID>`), or close idf.py monitor / other serial tool.

### A4. Wrong port

**Symptom**: data received but wrong firmware / garbled output.

When multiple boards are connected, `/dev/ttyACM0` may not be your board.

Fix: use `usb_serial` in board config to pin the device:
```bash
udevadm info /dev/ttyACM0 | grep ID_SERIAL_SHORT
# Compare against board config usb_serial field
```

---

## Section B — Class A board (dual USB): port missing

Board has a USB-UART bridge chip. The bridge port disappeared.

### B1. Bridge disconnected / cable issue
```bash
dmesg | tail -20   # look for USB disconnect/connect events
```
- Check USB cable and hub
- Try a different cable or direct connection (no hub)

### B2. Firmware crash (bridge stays up!)
Key property of Class A: **the bridge chip is independent hardware**.
Even if ESP32 firmware crashes completely, the bridge port stays present.

- Console still readable → connect and read crash log
- `idf.py -p /dev/ttyACM0 monitor` to see the crash reason
- Auto-reset via RTS/DTR should work: `idf.py -p /dev/ttyACM0 flash`

### B3. Board in ROM download mode
```bash
# Read what's on the port
python3 -c "
import serial
s = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
print(repr(s.read(200)))
"
```
If output contains `waiting for download` → bridge port shows ROM mode.

Fix: esptool can reset via RTS/DTR on Class A boards:
```bash
python3 -m esptool --chip auto -p /dev/ttyACM0 --before default_reset run
```

---

## Section C — Class B board (native-USB-only): port missing

This is the most common and most serious scenario.
The USB port IS the console — if firmware crashes, the port disappears.

### C1. Normal — firmware running, port should be there
```bash
dmesg | tail -10
# Look for: usb 1-x: new full-speed USB device number Y using xhci_hcd
# Then:     usb 1-x: New USB device found, idVendor=303a, idProduct=1001
# Then:     cdc_acm 1-x:1.0: ttyACM0: USB ACM device
```
If these lines appear, the port should be `/dev/ttyACM0` (or whichever number).

### C2. Firmware crashed — port disappeared

**Symptom**: port was there, AEL ran, now `ls /dev/ttyACM*` shows nothing.

This is expected behavior for Class B. The USB Serial/JTAG peripheral is in firmware.
When firmware crashes, USB stack dies, device disconnects.

**Recovery procedure** (Class B manual recovery):
1. **Do not power-cycle** — that may not help if bootloader also has issues
2. Enter download mode:
   - Hold **BOOT button** (GPIO0) down
   - While holding BOOT: press and release **RESET button**
   - Release BOOT
   - Wait 1–2 seconds
3. Check if port reappeared:
   ```bash
   ls /dev/ttyACM*
   dmesg | tail -5
   ```
   Expected: device re-enumerates as Espressif USB Serial/JTAG (same VID/PID)
4. Re-flash:
   ```bash
   cd /path/to/project
   idf.py -p /dev/ttyACM0 flash
   # or
   python3 -m esptool --chip esp32s3 -p /dev/ttyACM0 write_flash @build/flash_args
   ```

### C3. Device enumerated but no ttyACM (driver issue)
```bash
lsusb | grep -i espressif
# Should show: Bus XXX Device YYY: ID 303a:1001 Espressif USB JTAG/serial debug unit
```
If `lsusb` shows the device but no `/dev/ttyACM*`:
```bash
lsmod | grep cdc_acm    # should be loaded
modprobe cdc_acm        # if not loaded
```

### C4. USB port remains but stuck in ROM downloader

This can happen if flash completed but hard-reset left device in ROM mode.

**Symptom**: port exists, but log shows only:
```
waiting for download
```

Fix options:
1. **Physical reset**: press RESET button (without BOOT) → device reboots to app
2. **esptool run command** (if firmware was already flashed):
   ```bash
   python3 -m esptool --chip esp32s3 -p /dev/ttyACM0 \
     --before no_reset --after watchdog_reset run
   ```
3. **Re-flash**: if reset doesn't help, re-flash from scratch

---

## Section D — Flash fails

### D1. "no serial port found"
```
Flash: no serial port found
```
- No `/dev/ttyACM*` at all → firmware not running, board not enumerated
- For Class B: enter BOOT+RESET download mode first
- Then retry

### D2. Flash hangs at "Connecting..."
```
esptool.py: Connecting....._____....._____
```
- Device is not in a flashable state
- For Class B: enter BOOT+RESET download mode
- For Class A: `--before default_reset` should work via RTS/DTR

### D3. Flash fails mid-write (timeout/error)
- USB cable quality issue → try different cable, direct port
- Hub causing instability → connect directly to host USB
- Baud too high → try `baud: 115200` instead of 460800 in board config

---

## AEL Behavior Reference

| Scenario | AEL Response | Manual action needed |
|----------|-------------|---------------------|
| Port missing (Class B, firmware crashed) | Reports failure, requests manual recovery | BOOT+RESET → port reappears |
| Port missing (Class A, firmware crashed) | Reports failure | Bridge still up; re-flash via bridge |
| `bytes_read=0`, `baud=null` bug (pre-fix) | Misleading "ROM downloader" hint | Update AEL (fix applied 2026-03-24) |
| `bytes_read=0`, port was locked | `failed to open UART port` hint | Kill process holding port |
| Patterns missing | Lists `missing_expect` patterns | Re-check patterns against actual log |
| Permission denied | Clear error message | `usermod -a -G dialout` |

---

## Board-Specific Notes

### ESP32JTAG Instrument S3

- USB VID=303a PID=1001 serial=3C:DC:75:5A:9A:FC
- Single native USB → Class B rules apply
- BOOT button: GPIO0
- Boot complete: `[APP] Free memory:` at ~4.4s after reset
- Heartbeat: `Free internal and DMA memory:` every 3s
- After recovery flash: firmware boots normally, USB re-enumerates within 2s

### ESP32-C5 / ESP32-C6 DevKit Dual USB

- CH341 bridge: VID=1a86, UART0 console → Class A behavior on bridge port
- Espressif native: VID=303a, for flash → Class B behavior on native port
- If native USB disappears: switch to bridge for console; re-flash via bridge

---

*Derived from ESP32JTAG Firmware Brownfield Onboarding, 2026-03-24.*
*CE: `7daa8c80` (USB classification), `92fd939d` (brownfield pattern).*
