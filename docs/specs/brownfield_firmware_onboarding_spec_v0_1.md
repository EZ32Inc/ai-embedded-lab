# AEL Brownfield Firmware Onboarding — Spec v0.1

Derived from real execution: ESP32JTAG firmware (ESP32-S3) onboarding.
Date: 2026-03-24

---

## 1. What is Brownfield Onboarding?

Brownfield onboarding is the process of bringing an existing, already-compiling
firmware project into AEL's build → flash → observe → validate pipeline.

Contrast with Greenfield: Greenfield starts from an AEL template and is authored
inside `firmware/targets/`. Brownfield starts from a real-world project that
lives outside AEL's standard directories and already has its own build system,
structure, and conventions.

---

## 2. Brownfield vs Greenfield: Key Differences

| Dimension             | Greenfield                          | Brownfield                            |
|-----------------------|-------------------------------------|---------------------------------------|
| `project_dir`         | `firmware/targets/<name>` (internal)| External absolute path                |
| Build artifacts       | Predictable, AEL-named              | Project-specific names and layout     |
| Flash                 | Single .bin, standard               | May be multi-binary (flash_args)      |
| Observe               | GPIO/LA waveforms                   | Serial log, network, or none          |
| Validate              | LA edge counts or UART patterns     | Serial log patterns, health checks    |
| DUT role              | Always DUT                          | May be Instrument firmware            |

---

## 3. USB Console Type Classification

Before designing the observe/flash model, always determine the USB architecture.
This is the single most important question for ESP32-S3 (and ESP32-C3/C6) projects.

### Type A — Dual USB (bridge chip present)

```
ESP32-S3 UART0 (GPIO43/44) ──→ USB-to-UART bridge (CH340/CP2102) ──→ USB connector A
ESP32-S3 native USB (GPIO19/20) ────────────────────────────────────→ USB connector B
```

- Flash: UART bridge port (auto-reset via RTS/DTR works)
- Console: UART bridge port (standard baud-rate serial)
- Native USB port: optional, may expose JTAG

### Type B — Single native USB (NO bridge chip) ← ESP32JTAG case

```
ESP32-S3 native USB (GPIO19/20) ──────────────────────────────────→ USB connector (only one)
```

`sdkconfig` signal: `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` or `CONFIG_ESP_CONSOLE_USB_CDC=y`

**Consequences for AEL**:

| Capability | Type A (bridge) | Type B (native only) |
|------------|-----------------|----------------------|
| Auto-reset via RTS/DTR | ✓ | ✗ — MUST NOT attempt |
| Auto-enter download mode | ✓ | ✗ — manual BOOT+RESET |
| Console baud rate | relevant | irrelevant (USB CDC) |
| Console survives firmware crash | depends | NO — USB stack in firmware |
| Flash while running | ✓ | ✓ (if firmware/USB healthy) |
| Recovery when USB lost | auto | manual only |

**Detection**:
```bash
grep CONFIG_ESP_CONSOLE /path/to/sdkconfig
# CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y  → Type B
# CONFIG_ESP_CONSOLE_UART_DEFAULT=y     → Type A (UART console)
# CONFIG_ESP_CONSOLE_USB_CDC=y          → Type B variant
```

---

## 4. Flash and Recovery Model for Native USB (Type B)

### Normal flash path (firmware healthy, USB up)

```bash
cd /path/to/project
idf.py -p /dev/ttyACM0 flash
# OR
esptool.py --chip esp32s3 -p /dev/ttyACM0 -b 460800 write_flash @build/flash_args
```

No reset signal needed before flashing — ESP-IDF's esptool handles the
USB-JTAG stub protocol to trigger download mode when the firmware is running.

### Manual recovery path (firmware crashed / USB path lost / brick)

AEL **cannot** automate this. When the USB console disappears or flash fails,
AEL must request user intervention:

```
[AEL → user] Manual recovery required:
  1. Hold BOOT button (GPIO0) on the ESP32JTAG board
  2. While holding BOOT, press and release the RESET button
  3. Release BOOT
  4. Board enters ESP32-S3 download mode
  5. Confirm: /dev/ttyACM0 reappears (may get new path)
  6. AEL will retry flash
```

### AEL config flags

```yaml
flash:
  auto_reset: false              # never touch RTS/DTR
  requires_running_firmware: true
  recovery:
    method: manual_boot_button
    trigger_conditions:
      - firmware_crash
      - usb_stack_failure
      - brick_recovery

console:
  rts_dtr_reset: false
  loss_on_crash: true
```

---

## 5. Brownfield Onboarding Phases

### Phase 0 — Reconnaissance

Goals: understand the project before touching AEL.

Checklist:
- [ ] Identify build system (CMake/Make/other) and build command
- [ ] Locate artifact outputs (.elf, .bin, flash_args)
- [ ] Determine flash method (USB serial, JTAG, OTA)
- [ ] Determine observation path (serial log, GPIO, network, none)
- [ ] Identify device role (DUT / Instrument / Hybrid)
- [ ] Check if USB port is permanent or flash-only

For ESP32-IDF projects, always check:
```
grep CONFIG_ESP_CONSOLE /path/to/project/sdkconfig
```
- `CONFIG_ESP_CONSOLE_UART_DEFAULT=y` → UART0 console (separate from USB flash port)
- `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` → USB console on same port as flash (permanent)
- `CONFIG_ESP_CONSOLE_USB_CDC=y` → USB CDC console (permanent)

### Phase 1 — Build Integration

Config fields needed:
```yaml
build:
  type: idf                          # or make, cmake, etc.
  project_dir: /absolute/path        # external path OK
  artifact_stem: <firmware_name>
  idf_target: esp32s3               # only for idf type
  use_flash_args: true              # set if project uses flash_args multi-binary
```

Validation: run `idf.py build` manually, confirm artifacts appear.

### Phase 2 — Flash Integration

For ESP-IDF projects with `build/flash_args`:
```yaml
flash:
  method: idf_esptool
  use_flash_args: true
  port: null                        # probe at runtime
  usb_vid: "303a"                   # Espressif native USB JTAG/serial
  usb_pid: "1001"
  usb_serial: "<MAC>"               # stable identifier
  baud: 460800
```

USB port identification:
```bash
udevadm info /dev/ttyACM0 | grep ID_SERIAL
lsusb | grep Espressif
```

### Phase 3 — Observe: Serial Log as Primary Channel

When USB port is permanent (CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG or USB_CDC):

```json
"observe_uart": {
  "enabled": true,
  "port": "/dev/ttyACM0",
  "usb_vid": "303a",
  "usb_pid": "1001",
  "usb_serial": "<MAC>",
  "baud": null,
  "profile": "espidf",
  "duration_s": 15,
  "expect_patterns": [
    "<fpga_or_hw_init_ok_signal>",
    "<service_listening_signal>",
    "<app_ready_signal>"
  ]
}
```

Pattern identification process:
1. Reset device and capture full boot log
2. Identify: hardware init OK, service start, final ready signal
3. Pick 3–5 patterns that are stable across runs
4. Prefer signals near end of boot (closer to operational state)

For ESP32JTAG firmware specifically:
- `"FPGA configured OK - status = 0"` — FPGA hardware ready
- `"Listening on TCP port: 4242"` — GDB service up
- `"[APP] Free memory:"` — all init done (primary ready signal)
- `"Free internal and DMA memory:"` — heartbeat (periodic)

### Phase 4 — Validate

For instrument firmware with network services:
```json
"validate_network": {
  "source": "serial_log",
  "ip_pattern": "IP          : (\\d+\\.\\d+\\.\\d+\\.\\d+)",
  "checks": [
    {"kind": "ping",  "target": "{{observed_ip}}"},
    {"kind": "tcp",   "target": "{{observed_ip}}:4242"}
  ]
}
```

Key insight: for DHCP-assigned IPs, extract IP from serial log rather than
hardcoding it. Pattern: `"IP          : <ip>"` appears in network_mngr.c log.

### Phase 5 — AEL Config Files

Files to create:
1. `configs/boards/<board_id>.yaml` — board/device config
2. `tests/plans/<name>_smoke.json` — smoke test plan
3. `projects/<id>/project.yaml` — project-level metadata
4. (optional) `docs/specs/` — onboarding notes

---

## 4. Instrument Firmware vs DUT Firmware

When the firmware IS the instrument (e.g. ESP32JTAG probe firmware):

- `kind: instrument_firmware` in board config (not `kind: board`)
- No `observe_map` / LA wiring section
- No `bench_connections`
- Validate via serial log + network health, not GPIO waveforms
- Flash is a maintenance/update operation, not a per-test step

---

## 5. Multi-Binary Flash (`use_flash_args`)

ESP-IDF projects produce a `build/flash_args` file:
```
--flash_mode dio --flash_freq 80m --flash_size 16MB
0x0       bootloader/bootloader.bin
0x20000   esp32jtag_firmware.bin
0x8000    partition_table/partition-table.bin
0xf000    ota_data_initial.bin
```

When `use_flash_args: true` is set:
- Flash runner uses `esptool.py write_flash @build/flash_args` from project_dir
- Covers bootloader + app + partition table + OTA data in one operation
- Equivalent to `idf.py flash`

---

## 6. Grounded Insights from ESP32JTAG Case

1. **USB console type matters**: always check sdkconfig before assuming UART.
   USB_SERIAL_JTAG means the console is on the same USB connector as flash.

2. **DHCP IPs are not stable identifiers**: use USB serial number or MAC for
   device identification. Extract IP from serial log at runtime.

3. **Serial log is richer than GPIO**: boot log gives hardware init status,
   WiFi IP, service start — far more diagnostic than a GPIO edge count.

4. **Heartbeat signals enable liveness monitoring**: `"Free internal and DMA memory:"`
   every 3 seconds means we can detect a stuck device at runtime.

5. **Instrument firmware has no DUT observe_map**: skip LA wiring entirely.
   The instrument observes others; it doesn't need to be observed via GPIO.

---

## Reference: ESP32JTAG Firmware Files

| File | Purpose |
|------|---------|
| `configs/boards/esp32jtag_instrument_s3.yaml` | Board config |
| `tests/plans/esp32jtag_firmware_smoke.json` | Smoke test plan |
| `projects/esp32jtag_firmware_onboarding/project.yaml` | Project metadata |
| `/nvme1t/work/esp32jtag_firmware/` | Source project (external) |
