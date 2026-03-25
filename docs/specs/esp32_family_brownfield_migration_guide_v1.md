# ESP32 Family Brownfield Migration Guide v1
# AEL Family-Level Knowledge — ESP32 / ESP-IDF Projects

Scope: any ESP32-family MCU (S3, C5, C6, C3, original ESP32) running ESP-IDF,
migrated into AEL from a manually-working state.

Derived from: ESP32JTAG firmware brownfield migration (2026-03-24, first case).
Validated on: ESP32-S3 (native USB), ESP32-C5, ESP32-C6.

This guide belongs at the FAMILY layer — it applies to all ESP32/ESP-IDF brownfield
projects, regardless of what the firmware does or what peripherals are attached.

---

## 1. The One Question That Changes Everything

**Does this board have a USB-to-UART bridge chip?**

This single question determines the entire flash/console model.

### Type A — Dual USB (bridge chip present)

```
ESP32 UART0 (GPIO43/44 on S3) ──→ CH340 / CP2102 / FTDI ──→ USB port A
ESP32 native USB (GPIO19/20)  ──────────────────────────→ USB port B (optional)
```

Detection:
- Two USB connectors on the board, OR one USB + one UART header
- `sdkconfig: CONFIG_ESP_CONSOLE_UART_DEFAULT=y`

AEL consequences:
- Flash: UART bridge port, RTS/DTR auto-reset **works**
- Console: UART bridge, baud matters (typically 115200)
- Console survives firmware crash (bridge chip is external)
- Auto-enter download mode: works

### Type B — Single native USB (NO bridge chip)

```
ESP32-S3/C3/C5/C6 native USB (GPIO19/20) ──────────────→ USB connector (only one)
```

Detection:
- Single USB connector only
- `sdkconfig: CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` OR `CONFIG_ESP_CONSOLE_USB_CDC=y`
- `lsusb` shows VID=303a (Espressif native USB)

AEL consequences:
- Flash: native USB stub protocol, **no RTS/DTR** — must use `auto_reset: false`
- Console: USB CDC/JTAG, **baud=null** (USB CDC ignores baud rate)
- Console **disappears** on firmware crash — USB stack is in firmware
- Recovery: manual BOOT+RESET required — AEL cannot auto-recover

```bash
# Detection command
grep CONFIG_ESP_CONSOLE /path/to/project/sdkconfig
# CONFIG_ESP_CONSOLE_UART_DEFAULT=y     → Type A
# CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y  → Type B
# CONFIG_ESP_CONSOLE_USB_CDC=y          → Type B variant
```

---

## 2. The Three Build Risks

Every ESP32-IDF brownfield migration must handle these before AEL touches the build:

### Risk 1 — `idf.py` not in PATH

Many projects have a project-specific IDF install. Check:
```bash
which idf.py || echo "NOT IN PATH"
```

If not found:
```yaml
build:
  idf_path: /home/user/esp/esp-idf   # absolute path to IDF root
```

### Risk 2 — Tuned sdkconfig gets destroyed

If the project has a committed, tuned `sdkconfig` (custom flash size, disabled components,
custom features), running `idf.py set-target` **wipes it entirely** and replaces with defaults.

Check:
```bash
git log -- sdkconfig   # any commits? tuned.
```

If tuned/committed:
```yaml
build:
  skip_set_target: true   # AEL will NOT run idf.py set-target
```

If fresh/untuned:
```yaml
build:
  skip_set_target: false  # AEL can safely set-target
```

### Risk 3 — Multi-binary flash (flash_args)

Modern ESP-IDF projects produce multiple binaries (bootloader, app, partition table, OTA data).
Do not assume single-binary flash.

Check:
```bash
cat /path/to/project/build/flash_args
```

If present (most real projects):
```yaml
flash:
  use_flash_args: true   # uses esptool write_flash @build/flash_args
```

If absent (simple projects):
```yaml
flash:
  use_flash_args: false  # uses single .bin
```

---

## 3. Observe Model Selection

For ESP32 brownfield, choose observe model based on firmware type:

### Model A — Instrument firmware (no DUT)

The firmware itself is the instrument (e.g., ESP32JTAG probe firmware).
Validate via serial log + network — no GPIO waveforms.

```json
"observe_uart": {
  "enabled": true,
  "port": "/dev/ttyACM0",
  "usb_vid": "303a",
  "usb_pid": "1001",
  "baud": null,
  "profile": "espidf",
  "duration_s": 15,
  "expect_patterns": [
    "<subsystem_init_ok>",
    "<service_ready>",
    "<app_ready>"
  ]
}
```

For DHCP IPs, extract from log — never hardcode:
```json
"validate_network": {
  "source": "serial_log",
  "ip_pattern": "IP          : (\\d+\\.\\d+\\.\\d+\\.\\d+)"
}
```

### Model B — DUT firmware (GPIO/LA verification)

The firmware is the device under test. Validate via GPIO edges or PCNT loopback.
See `ael/patterns/loopback/pcnt_loopback.py` for the minimal 1-wire loopback pattern.

---

## 4. Boot Log — How to Extract Stable Patterns

**Do not guess patterns. Always capture the real boot log first.**

```bash
# Capture boot log (works for both Type A and Type B)
idf.py -p /dev/ttyACM0 -C /path/to/project monitor
# Then press RESET to see full boot sequence
```

Good patterns (stable across runs):
- Hardware subsystem init OK: `"FPGA configured OK"`, `"SPI master init"`, `"I2C init OK"`
- Service ready: `"Listening on TCP port: NNNN"`, `"HTTP server started"`
- Final boot-complete line: `"[APP] Free memory:"`, `"System ready"`
- Network up: `"GOT ip event!!!"`, `"Connected to AP"`

Bad patterns (avoid):
- Memory addresses: `"0x3ffb..."` — changes per build
- Timing-dependent: `"(1234ms)"` — varies
- Version strings: `"v1.2.3-abc"` — changes per build
- Conditional: only appears when some feature is enabled

Pick 3–5 patterns. Include one near end of boot. Include heartbeat if available.
Size `duration_s` = observed_boot_time_s + 5s (minimum 15s).

---

## 5. ESP32-Specific Pitfalls (Known, Validated)

### Pitfall 1 — baud=null TypeError  [CE: `da6927bd`]

AEL `observe_uart` adapter calls `int(baud)` internally.
For native USB boards, `baud: null` in YAML → `int(None)` → TypeError crash.

**Status:** Fixed 2026-03-24. Always verify AEL adapter handles `baud=null` before using.
**Workaround if not fixed:** set `baud: 115200` (USB CDC ignores it anyway).

### Pitfall 2 — RTS/DTR on native USB  [CE: `7daa8c80`]

Attempting DTR reset on a native-USB-only board causes inconsistent behavior:
sometimes enters download mode, sometimes does nothing, sometimes crashes.

**Rule:** If `usb_interface_type: native_only`, always set `console.rts_dtr_reset: false`.

### Pitfall 3 — skip_set_target omission destroys sdkconfig  [CE: `92fd939d`]

Running `idf.py set-target esp32s3` on a project with tuned sdkconfig silently replaces
all custom settings (flash size, components, UART config) with defaults.

**Rule:** Always check `git log -- sdkconfig`. If tuned, set `skip_set_target: true`.

### Pitfall 4 — Console loss on crash (native USB)

If the firmware crashes, the USB stack goes with it. `/dev/ttyACM0` disappears.
AEL must treat a missing port as a crash indicator, not a configuration error.

**Rule:** Set `console.loss_on_crash: true` for all native USB boards.
**Recovery:** Request user to perform BOOT+RESET. Cannot be automated.

### Pitfall 5 — DHCP IP instability

DHCP IPs change between reboots. Never hardcode DHCP IPs in test plans.
Extract from serial log at runtime.

**Rule:** Use `ip_pattern` regex in `validate_network.source: serial_log`.
Store observed IP in `project.yaml` as `dhcp_ip_observed` — reference only, not config.

---

## 6. Hypothesis Confirmation Template

Use this before executing any ESP32 brownfield migration.
Fill in from discovery, then confirm with user in one message:

```
AEL ESP32 Brownfield Migration — Hypothesis Confirmation

Board: <board_name>
Project: <project_path>

Discovered:
  MCU:            <esp32s3 / esp32c5 / esp32c6 / ...>
  Build:          ESP-IDF CMake at <project_path>
  IDF version:    <from idf.py --version>
  USB type:       [Type A: dual USB / Type B: single native USB]
  USB device:     /dev/ttyACM<N>, VID=<vid> PID=<pid>
  sdkconfig:      [tuned+committed / fresh] → skip_set_target=[true/false]
  Flash layout:   [multi-binary flash_args / single binary]
  Firmware role:  [instrument firmware / DUT firmware]
  Network:        [DHCP WiFi / static / none]

Assumptions I will act on (correct if wrong):
  [1] USB type: <A or B> — RTS/DTR reset: <yes/NO>
  [2] skip_set_target: <true/false>
  [3] idf_path: <in PATH / at path>
  [4] Flash: <use_flash_args: true/false>
  [5] Observe via: <serial log / GPIO / network>
  [6] Recovery: <auto RTS/DTR / manual BOOT+RESET>

Any corrections?
```

---

## 7. Board YAML Quick Reference

Minimum required fields for ESP32 brownfield board config:

```yaml
# ── Identity ──────────────────────────────────────────────
id: <board_id>
mcu: <esp32s3 | esp32c5 | esp32c6>
kind: <board | instrument_firmware>

# ── Build ─────────────────────────────────────────────────
build:
  type: idf
  project_dir: /absolute/path/to/project
  idf_target: <esp32s3 | esp32c5 | esp32c6>
  skip_set_target: <true | false>       # true if sdkconfig is tuned
  idf_path: <null | /path/to/idf>       # null if idf.py in PATH
  use_flash_args: <true | false>

# ── Flash ─────────────────────────────────────────────────
flash:
  method: idf_esptool
  usb_vid: "303a"                        # Espressif native USB
  usb_pid: "1001"
  usb_serial: "<MAC>"
  auto_reset: <false>                    # false for Type B, true for Type A
  requires_running_firmware: true        # native USB needs running firmware

# ── Console ───────────────────────────────────────────────
console:
  port: /dev/ttyACM0
  type: <usb_serial_jtag | uart>         # usb_serial_jtag for Type B
  baud: <null | 115200>                  # null for Type B (USB CDC)
  rts_dtr_reset: <false | true>          # false for Type B
  loss_on_crash: <true | false>          # true for Type B
  usb_interface_type: <native_only | dual>

# ── Recovery ──────────────────────────────────────────────
recovery:
  method: <manual_boot_button | auto_rts_dtr>
```

---

## 8. CE Records from This Migration

| CE ID | Scope | Summary |
|-------|-------|---------|
| `92fd939d` | pattern | Brownfield firmware onboarding method (ESP32-S3 native USB) |
| `7daa8c80` | pattern | ESP32 USB interface classification (dual vs native-only) |
| `da6927bd` | pattern | observe_uart baud=null → int(None) TypeError (USB CDC) |

All three are `[HIGH_PRIORITY]` in CLAUDE.md.

---

## 9. Relationship to Other Documents

| Document | Layer | Relationship |
|----------|-------|-------------|
| `ael_universal_bringup_spec_v1.md` | AEL-core | Parent method — this guide is one instantiation |
| `brownfield_firmware_onboarding_spec_v0_1.md` | Family | Earlier version, ESP32-specific, instrument firmware focus; still valid |
| `brownfield_migration_checklist.md` | Family | Operational checklist, derived from same migration; complement to this guide |
| `esp32jtag_migration_method_record_v1.md` | Board | Concrete case record for ESP32JTAG — see that doc for board specifics |

---

*First version derived from ESP32JTAG Firmware Brownfield Onboarding, 2026-03-24.*
*Applies to any ESP32/ESP-IDF project: S3, C5, C6, C3, original ESP32.*
