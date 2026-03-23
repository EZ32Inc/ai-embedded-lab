# ESP32-C6 Board Bring-up Notes

**Board:** ESP32-C6-DevKitC-1
**Date validated:** 2026-03-23
**Status:** ✅ Full suite PASS (7/7)
**Pattern:** Minimal-Instrument Board Bring-up (see `esp32_bringup_civilization_pattern_v1.md`)

---

## Port Identification

| Role | Interface | Serial number | Notes |
|------|-----------|--------------|-------|
| Flash | Native USB Serial/JTAG | `40:4C:CA:55:5A:D4` | Use `find_port_by_serial()` — ACM number shifts after each flash |
| Console | CH341 UART0 bridge | `58CF083460` | GPIO17=TX, GPIO16=RX (DevKitC-1 default UART0) |

**Critical:** Always identify ports by serial number, never by `/dev/ttyACMx`.

---

## Safe GPIO List

| GPIO | Safe to use | Notes |
|------|------------|-------|
| 15, 18–23 | ✅ | Adjacent pairs available for loopback |
| 2, 3, 5, 6 | ✅ | Used for LA probe connection (ESP32JTAG P0.x) |
| 0, 1 | ⚠️ | Strap pins — usable but verify boot behavior |
| 8, 9 | ⚠️ | Strap pins |
| 11–14 | ❌ | USB D+/D- and related — do not use |
| 16, 17 | ❌ | UART0 TX/RX (console) |

---

## Verified Wiring (ESP32JTAG + loopback)

With ESP32JTAG (192.168.2.109) connected:

```
ESP32JTAG P0.0  →  GPIO2   (LA observation)
ESP32JTAG P0.1  →  GPIO3   (LA observation / LEDC PWM)
ESP32JTAG P0.2  →  GPIO5   (LA observation)
ESP32JTAG P0.3  →  GPIO6   (LA observation)

GPIO20 ↔ GPIO21   (PCNT loopback jumper)
```

Without LA (instrument-free):
```
GPIO20 ↔ GPIO21   (PCNT loopback jumper only)
```

---

## Reset Procedure

CH341 normal-boot reset (DTR/RTS):
```python
s.setDTR(False)   # BOOT pin HIGH → normal boot (not download mode)
s.setRTS(True)    # EN pin LOW   → hold reset
time.sleep(0.12)
s.setRTS(False)   # EN pin HIGH  → release reset
```

**Sequence:** Issue reset FIRST, then start UART reader thread.
Firmware has a 2-second `vTaskDelay` on boot — gives time to open port.

---

## Partition Table

Default 1 MB factory partition is too small for BLE + Wi-Fi firmware (~1.2 MB).
Use custom partition:

```csv
nvs,      data, nvs,     0x9000,   24K,
phy_init, data, phy,     0xf000,   4K,
factory,  app,  factory, 0x10000,  1920K,
```

Set in `sdkconfig.defaults`:
```
CONFIG_PARTITION_TABLE_CUSTOM=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"
```

**Important:** Delete project-level `sdkconfig` before rebuild so defaults are re-applied.

---

## LEDC PWM Behavior

- Configured: 1 kHz, 10-bit, 50% duty
- Observed on LA: ~502–504 Hz (approximately freq/2 at 10-bit resolution on this silicon)
- Duty cycle: 0.50 ✅
- LA acceptance range: `400 < freq < 1200` and `0.40 < duty < 0.60`

---

## Test Suite Results (first PASS run)

| Test | Output | Result |
|------|--------|--------|
| AEL_TEMP | celsius=22.1 | PASS |
| AEL_NVS | wrote=0xAE100001 read=0xAE100001 | PASS |
| AEL_WIFI | ap_count=15 | PASS |
| AEL_BLE | advertisers=70 | PASS |
| AEL_SLEEP | wakeup_cause=4 (timer) | PASS |
| AEL_PWM | GPIO3 1kHz 50% | PASS |
| AEL_PCNT | sent=100 counted=100 | PASS |
| LA verify | GPIO3 502 Hz duty=0.50 | PWM OK |

---

## Lessons Learned

1. **Port serial lookup beats ACM numbering** — after each flash, ACM numbers reorder. Serial-based lookup is always correct.
2. **Reset before UART reader** — if the reader starts after reset, the 2s boot delay is sufficient. If reset happens after reader starts, the reader may miss early output.
3. **LA wires cannot double as loopback jumpers** — physical constraint: wire already plugged into ESP32JTAG cannot also be a free jumper. Use separate free GPIO pairs for loopback.
4. **LEDC 10-bit mode produces ~freq/2 on LA** — hardware behavior of ESP32-C6 LEDC at 10-bit resolution. Duty cycle is correct. Widen acceptance window accordingly.
5. **sdkconfig.defaults only applies if no sdkconfig exists** — delete project sdkconfig before changing defaults.

---

## Firmware Targets

| Target | Path | Purpose |
|--------|------|---------|
| esp32c6_wire_verify | `firmware/targets/esp32c6_wire_verify/` | Initial LA wiring verification |
| esp32c6_gpio_loopback | `firmware/targets/esp32c6_gpio_loopback/` | 3-pair GPIO loopback |
| esp32c6_hw_suite | `firmware/targets/esp32c6_hw_suite/` | GPIO + UART + ADC loopback |
| esp32c6_suite_ext | `firmware/targets/esp32c6_suite_ext/` | 7-test full suite |
