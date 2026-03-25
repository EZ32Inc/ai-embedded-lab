# ESP32 USB Interface Classification — AEL Board/Instrument Model

## Overview

ESP32 boards expose USB connectivity in two fundamentally different architectures.
AEL must distinguish them because they have different reset/recovery capabilities.
Incorrectly assuming RTS/DTR is available causes silent failures and incorrect recovery guidance.

---

## Classification

### Class A — Dual-Interface (bridge + native)

**Definition**: Board has both a dedicated USB-to-UART bridge chip AND the ESP32 native USB port.

**Examples**:
- ESP32-C5 DevKit (CH341 bridge + native USB Serial/JTAG)
- ESP32-C6 DevKit (CH341 bridge + native USB Serial/JTAG)
- Most official Espressif DevKitC boards with separate "UART" and "USB" connectors

**Properties**:
- Bridge port (e.g., `/dev/ttyACM0` CH341): UART0 console, flash via UART
  - RTS/DTR **available** → auto-reset and download-mode entry work
  - Console survives firmware crash (bridge is independent silicon)
- Native port (e.g., `/dev/ttyACM2` Espressif): USB Serial/JTAG, flash via USB
  - No RTS/DTR from host side (USB JTAG protocol handles its own reset)
- AEL `reset_strategy: rts` safe on bridge port

**Board YAML**:
```yaml
usb_interface_type: dual
console:
  type: uart          # or usb_serial_jtag if using native port for console
  rts_dtr_reset: true # only if using bridge port
```

---

### Class B — Native-USB-Only (no bridge chip)

**Definition**: Single USB port wired directly to ESP32 native USB peripheral (GPIO19/20 on S3, etc.).
No separate USB-to-UART bridge chip on the board.

**Examples**:
- ESP32JTAG Instrument S3 (ESP32-S3 with single USB-C to native USB)
- ESP32-S3-WROOM bare modules
- Many custom/minimal ESP32 boards

**Properties**:
- Console type: `usb_serial_jtag` (CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y)
- RTS/DTR lines **do NOT control reset or boot mode** — no bridge chip
- Console is implemented in firmware → **disappears if firmware crashes or USB stack fails**
- Flash assumes firmware is healthy (can also use USB JTAG stub)
- Recovery: must physically hold BOOT + press RESET to enter download mode

**Board YAML**:
```yaml
usb_interface_type: native_only
console:
  type: usb_serial_jtag
  rts_dtr_reset: false    # hard constraint: no bridge, no RTS/DTR
  loss_on_crash: true
flash:
  auto_reset: false        # no RTS/DTR reset
```

---

## AEL Enforcement

`strategy_resolver.build_uart_step()` reads the board config and enforces the constraint:

```python
# Detect native-USB-only (Class B) boards
_native_usb = (
    console.type == "usb_serial_jtag"
    OR console.rts_dtr_reset == False
    OR board.usb_interface_type == "native_only"
)
if _native_usb:
    observe_uart_cfg["reset_strategy"] = "none"      # override, not setdefault
    observe_uart_cfg["auto_reset_on_download"] = False
```

This ensures AEL never attempts RTS/DTR-based recovery on native-USB boards,
even if the test plan inadvertently sets `auto_reset_on_download: true`.

---

## Recovery Model

| Class | Firmware running | Firmware crashed / USB gone |
|-------|-----------------|----------------------------|
| A (dual) | Normal flash/observe via bridge or native | Console still available via bridge; re-flash via bridge |
| B (native only) | Normal flash/observe via native USB | Console gone; AEL must request manual BOOT+RESET |

---

## Detection Heuristics

If `usb_interface_type` is not set explicitly, AEL can infer Class B from:
- `console.type == "usb_serial_jtag"` — always implies native USB
- `console.rts_dtr_reset == false` — explicit flag
- Single USB connector in board description (human-declared)

Default assumption when nothing is set: Class A (permissive, allows RTS/DTR).
**Best practice**: always set `usb_interface_type` explicitly in board YAML.

---

## Board Config Fields Summary

| Field | Values | Class A | Class B |
|-------|--------|---------|---------|
| `usb_interface_type` | `dual`, `native_only`, `bridge_only` | `dual` | `native_only` |
| `console.type` | `uart`, `usb_serial_jtag` | `uart` (bridge) | `usb_serial_jtag` |
| `console.rts_dtr_reset` | `true`, `false` | `true` | `false` |
| `console.loss_on_crash` | `true`, `false` | `false` | `true` |
| `flash.auto_reset` | `true`, `false` | `true` | `false` |
| AEL `reset_strategy` | `rts`, `none` | `rts` (if bridge port) | `none` (forced) |

---

*Derived from ESP32JTAG Firmware Brownfield Onboarding session, 2026-03-24.*
*CE pattern: `7daa8c80` (USB interface classification), `92fd939d` (brownfield onboarding).*
