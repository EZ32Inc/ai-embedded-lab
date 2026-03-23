# ESP32-C5 Board Bring-up Notes

**Board:** ESP32-C5-DevKitC-1
**Date validated:** 2026-03-23
**Status:** ✅ Full suite PASS (7/7) — first run, zero errors
**Pattern:** Minimal-Instrument Board Bring-up (see `esp32_bringup_civilization_pattern_v1.md`)
**Derived from:** ESP32-C6 pattern (direct migration, no re-exploration)

---

## Port Identification

| Role | Interface | Serial number | Notes |
|------|-----------|--------------|-------|
| Flash | Native USB Serial/JTAG | `3C:DC:75:84:A6:54` | MAC-format serial |
| Console | CH341 UART0 bridge | `5AAF278818` | GPIO11=TX, GPIO12=RX |

**Critical:** Always identify ports by serial number, never by `/dev/ttyACMx`.

---

## Safe GPIO List

| GPIO | Safe to use | Notes |
|------|------------|-------|
| 0–7, 9, 15 | ✅ | Free for use |
| 2, 3 | ✅ | Verified PCNT loopback pair |
| 4 | ✅ | Verified LEDC PWM output |
| 8, 9 | ⚠️ | Strap pins — verify boot behavior |
| 11, 12 | ❌ | UART0 TX/RX (console) |
| 13, 14 | ❌ | USB D-/D+ |

---

## Verified Wiring (instrument-free)

Minimum wiring for full 7-test suite:

```
GPIO2 ↔ GPIO3   (PCNT loopback jumper — single wire)
USB flash cable   → Native USB port
USB console cable → CH341 USB port
```

No LA, no JTAG, no oscilloscope required.

---

## Reset Procedure

Same as ESP32-C6 — CH341 normal-boot reset:
```python
s.setDTR(False)   # BOOT pin HIGH → normal boot
s.setRTS(True)    # EN pin LOW   → hold reset
time.sleep(0.12)
s.setRTS(False)   # EN pin HIGH  → release reset
```

Issue reset FIRST, then start UART reader thread.

---

## Partition Table

Same requirement as C6 — BLE + Wi-Fi binary exceeds 1 MB default:

```csv
nvs,      data, nvs,     0x9000,   24K,
phy_init, data, phy,     0xf000,   4K,
factory,  app,  factory, 0x10000,  1920K,
```

---

## ESP32-C5 Specific: Dual-Band Wi-Fi

ESP32-C5 is the only low-power ESP32 with 5 GHz Wi-Fi support.
Use `esp_wifi_set_band_mode()` to scan each band separately:

```c
scan_band(WIFI_BAND_MODE_2G_ONLY, &cnt24);
scan_band(WIFI_BAND_MODE_5G_ONLY, &cnt5);
```

PASS condition: `cnt24 > 0 || cnt5 > 0`
(5 GHz may return 0 in environments without 5 GHz APs — not a failure.)

---

## sdkconfig.defaults

```
CONFIG_ESP_CONSOLE_UART_DEFAULT=y        # console on UART0 (GPIO11/12)
CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_160=y
CONFIG_BT_ENABLED=y
CONFIG_BT_NIMBLE_ENABLED=y
CONFIG_ESP_WIFI_ENABLED=y
CONFIG_PARTITION_TABLE_CUSTOM=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"
CONFIG_PARTITION_TABLE_OFFSET=0x8000
```

---

## Test Suite Results (first PASS run)

| Test | Output | Result |
|------|--------|--------|
| AEL_TEMP | celsius=22.1 | PASS |
| AEL_NVS | wrote=0xAE100001 read=0xAE100001 | PASS |
| AEL_WIFI | ap_2g=15 ap_5g=13 | PASS |
| AEL_BLE | advertisers=131 | PASS |
| AEL_SLEEP | wakeup_cause=4 (timer) | PASS |
| AEL_PWM | GPIO4 1kHz 50% | PASS |
| AEL_PCNT | sent=100 counted=100 | PASS |

**Time from C6 pattern to C5 PASS: ~5 minutes.**

---

## Lessons Learned

1. **Direct pattern migration works** — all C6 logic (reset, UART parsing, partition, NimBLE scan, PCNT) transferred to C5 without modification, only GPIO numbers and serial IDs changed.
2. **5G Wi-Fi scan is slow** — passive scan on 5 GHz can take 5–10 s. UART timeout must be ≥ 35 s for full dual-band suite.
3. **PCNT on GPIO2/GPIO3 works cleanly** — both pins are strap-safe and free from USB/UART conflicts on C5.
4. **No LA needed for first validation** — PWM self-test (driver config PASS) is sufficient for bring-up. LA can be added later for signal integrity verification.
5. **Chip revision in boot log** — ESP32-C5 prints `chip revision: v1.0`. Useful for debugging if behavior differs from datasheet.

---

## Firmware Targets

| Target | Path | Purpose |
|--------|------|---------|
| esp32c5_suite_ext | `firmware/targets/esp32c5_suite_ext/` | 7-test full suite |
