# observe_uart Boot Pattern Guide
# How to capture the boot log and extract stable expect_patterns

This guide answers the most common failure mode in new board onboarding:
`observe_uart` passes but expect_patterns are never matched.

The root cause is almost always that patterns were guessed rather than
extracted from a real boot log.

---

## Why patterns matter

`observe_uart` captures serial output for `duration_s` seconds after flash/reset,
then checks that every string in `expect_patterns` appears at least once.

If any pattern is missing → test FAILS with:
```
uart: expected UART patterns missing
missing_expect: ["your pattern here"]
```

There is no partial credit. One wrong pattern fails the whole check.

---

## Step 1 — Capture a real boot log

### Method A: idf.py monitor (recommended for ESP-IDF projects)

```bash
# Press RESET on the board while this is running, or flash first
idf.py -p /dev/ttyACM0 -C /path/to/project monitor 2>&1 | tee /tmp/bootlog.txt
# Ctrl+] to exit
```

For native USB boards: this works without any extra flags.
For bridge boards: replace `/dev/ttyACM0` with the bridge port.

### Method B: pyserial raw capture

```bash
python3 - << 'EOF'
import serial, time, sys
port = '/dev/ttyACM0'
baud = 115200  # use None/any value for native USB — CDC ignores it
s = serial.Serial(port, baud, timeout=0.1, rtscts=False, dsrdtr=False)
print(f"Capturing from {port} for 15s — press RESET on the board now")
start = time.time()
lines = []
while time.time() - start < 15:
    data = s.read(4096)
    if data:
        text = data.decode('utf-8', errors='replace')
        sys.stdout.write(text)
        sys.stdout.flush()
        lines.extend(text.splitlines())
s.close()
with open('/tmp/bootlog.txt', 'w') as f:
    f.write('\n'.join(lines))
print('\n\nSaved to /tmp/bootlog.txt')
EOF
```

### Method C: read existing run artifact

If AEL already ran (even if it failed), the raw log is saved:
```bash
cat runs/<run_id>/observe_uart.log
# or
ls runs/ | sort | tail -1  # find latest run
cat runs/<latest>/observe_uart.log
```

---

## Step 2 — Annotate the boot log

Open `/tmp/bootlog.txt`. A typical ESP-IDF boot looks like:

```
ESP-ROM:esp32s3-20210327                    ← ROM header (not in app log)
Build:Mar 27 2021
rst:0x1 (POWERON),boot:0x8 (SPI_FAST_FLASH_BOOT)   ← reset reason
...
I (0) boot: ESP-IDF v5.5-dev-...            ← IDF version (changes per build)
I (775) app_main: Starting                  ← app_main begins
I (1815) fpga: FPGA configured OK - status = 0      ← subsystem init
I (1820) spi: spi_master_init() done, gbl_spi_h1 is Not NULL
I (4395) wifi: GOT ip event!!!              ← network up
I (4395) wifi: IP          : 192.168.2.62  ← IP address (dynamic!)
I (4415) app: [APP] Free memory: 123456    ← boot complete (stable)
I (7415) app: Free internal and DMA memory: 123456  ← heartbeat (every 3s)
```

Mark each line as:
- ✓ STABLE — same text every boot
- ~ VARIABLE — contains address, timestamp, version, dynamic value
- ✗ CONDITIONAL — only appears in some conditions

---

## Step 3 — Select good patterns

### Rules for GOOD patterns

1. **Stable across boots** — appears every time, same text
2. **Not time-dependent** — does not contain exact millisecond timestamps
3. **Not address-dependent** — does not contain `0x3ff...`, `0x4...` addresses
4. **Subsystem-meaningful** — marks a real milestone (init done, service up, etc.)
5. **Not version-pinned** — if it contains IDF/app version, it breaks on every update

### Rules for BAD patterns (avoid)

| Type | Example | Why bad |
|------|---------|---------|
| Full line with timestamp | `I (775) app_main: Starting` | timestamp `775` varies |
| Memory address | `entry 0x40381b8c` | address changes per build |
| Free memory value | `[APP] Free memory: 123456 bytes` | value changes |
| IP address | `IP          : 192.168.2.62` | DHCP changes |
| IDF version string | `ESP-IDF v5.5-dev-3456abc` | changes per build |
| Conditional log | appears only if feature flag set | not always present |

### Recommended pattern selection strategy

Select 3–5 patterns covering different boot phases:

| Phase | What to select | Example |
|-------|---------------|---------|
| Subsystem init | Peripheral/driver "OK" or "done" line | `FPGA configured OK` |
| Service ready | Network/server listening line | `Listening on TCP port: 4242` |
| Boot complete | Final init message | `\[APP\] Free memory:` |
| Heartbeat (optional) | Periodic health log | `Free internal and DMA memory:` |

For the final boot-complete pattern: select the **text prefix** without the dynamic
numeric suffix. Example: `[APP] Free memory:` not `[APP] Free memory: 123456 bytes`.

---

## Step 4 — Escape regex special characters

`expect_patterns` values are Python regexes (case-insensitive).
These characters must be escaped with `\\`:

```
( ) [ ] { } . * + ? ^ $ | \
```

| Raw log text | Pattern to use |
|-------------|---------------|
| `spi_master_init() done` | `spi_master_init\\(\\) done` |
| `[APP] Free memory:` | `\\[APP\\] Free memory:` |
| `GOT ip event!!!` | `GOT ip event` (trailing `!` safe, or `GOT ip event!!!`) |
| `FPGA configured OK - status = 0` | `FPGA configured OK - status = 0` (no special chars) |
| `Listening on TCP port: 4242` | `Listening on TCP port: 4242` |

Test your patterns:
```python
import re
log_line = "spi_master_init() done, gbl_spi_h1 is Not NULL"
pattern = r"spi_master_init\(\) done"
print(bool(re.search(pattern, log_line, re.IGNORECASE)))  # True
```

---

## Step 5 — Set duration_s correctly

`duration_s` must be long enough to capture the full boot sequence:

```
duration_s ≥ (time from reset to final boot-complete line) + 3s margin
```

| Firmware | Typical boot time | Recommended duration_s |
|---------|------------------|----------------------|
| Minimal ESP32 app | ~0.5s | 8 |
| ESP32 + WiFi STA | ~3–5s | 15 |
| ESP32 + WiFi + FPGA init | ~4–5s | 15 |
| Complex init (sensors, SD, etc.) | 5–15s | 25 |

**When in doubt: use 20s.** The test just takes longer, it doesn't fail.
Too short = patterns missed = false failure.

---

## Step 6 — validate_network IP pattern

If the firmware prints its IP address in the boot log, you can extract it dynamically:

```json
"validate_network": {
    "source": "serial_log",
    "ip_pattern": "IP\\s+:\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)"
}
```

The `ip_pattern` is a regex with one capture group. AEL substitutes the
captured IP into `{{observed_ip}}` for subsequent ping/TCP checks.

Do NOT hardcode the IP in test plan — DHCP addresses change.

Common IP log formats:
```
# ESP-IDF WiFi
I (4395) wifi: IP          : 192.168.2.62
→ ip_pattern: "IP\\s+:\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)"

# lwIP event callback
I (4395) event: got ip: 192.168.2.62
→ ip_pattern: "got ip:\\s*(\\d+\\.\\d+\\.\\d+\\.\\d+)"

# Custom log
I (4395) net: assigned 192.168.2.62
→ ip_pattern: "assigned\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)"
```

---

## Quick checklist

- [ ] Boot log captured from real hardware (not guessed)
- [ ] ≥3 stable expect_patterns selected
- [ ] No patterns contain: addresses, millisecond timestamps, IP addresses, memory sizes
- [ ] Regex special chars escaped (`\\(`, `\\)`, `\\[`, `\\]`)
- [ ] `duration_s` ≥ boot time + 3s margin
- [ ] Patterns tested with `re.search()` against actual log lines
- [ ] IP pattern uses capture group `(\\d+\\.\\d+\\.\\d+\\.\\d+)` if network check needed

---

## Example: ESP32JTAG Firmware S3 (real, validated 2026-03-24)

```json
"observe_uart": {
    "enabled": true,
    "port": "/dev/ttyACM0",
    "baud": null,
    "profile": "espidf",
    "duration_s": 15,
    "expect_patterns": [
        "FPGA configured OK - status = 0",
        "spi_master_init\\(\\) done, gbl_spi_h1 is Not NULL",
        "Listening on TCP port: 4242",
        "\\[APP\\] Free memory:"
    ],
    "rts_dtr_reset": false
}
```

Boot timeline:
- t=0ms:    reset
- t=775ms:  app_main() starts
- t=1815ms: FPGA configured OK  ← pattern 1
- t=1820ms: spi_master_init() done  ← pattern 2
- t=4395ms: WiFi connected
- t=4415ms: Listening on TCP port  ← pattern 3
- t=4415ms: [APP] Free memory  ← pattern 4 (boot complete)

All 4 patterns captured within `duration_s=15`. ✓

---

*Derived from ESP32JTAG Firmware Brownfield Onboarding, 2026-03-24.*
