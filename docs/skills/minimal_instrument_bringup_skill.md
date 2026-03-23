# Minimal-Instrument Board Bring-up Skill

## Purpose

`minimal_instrument_bringup` is the AEL Civilization Engine skill for validating
a new ESP32 (or similar RISC-V MCU) board from scratch using only:

- Two USB cables (flash port + console port)
- One loopback jumper wire (for PCNT physical verification)
- No external instruments (no LA, no oscilloscope, no JTAG probe)

It encodes the experience gained from the ESP32-C6 → ESP32-C5 bring-up sequence,
where applying this pattern reduced bring-up time from ~5 hours to ~5 minutes with
zero errors on the first run.

See `docs/esp32_bringup_civilization_pattern_v1.md` for full background.

---

## When To Use

Invoke this skill whenever:

- Bringing up a new ESP32 board (any variant: C3, C5, C6, S3, H2, …)
- Migrating a validated bring-up pattern from one board to a similar board
- Needing to validate a board without external instruments available
- Starting bring-up of any RISC-V MCU with dual USB (flash + console)

Do not skip this skill just because the new board is "similar" to one already validated.
Similarity means **reuse the pattern**, not **skip the pattern**.

---

## Trigger Conditions

```yaml
trigger:
  - "bring up new board"
  - "new MCU, same family as X"
  - "validate [board] without instruments"
  - "first bring-up [chip]"
  - "port [existing test] to [new chip]"
```

---

## Core Flow (6 Steps)

### Step 1 — Board Definition

Identify and record before writing any firmware or wiring plan:

```
flash_serial:    <USB serial number of flash port>
console_serial:  <USB serial number of console port>
safe_gpio:       <list of GPIOs free from strap/USB/UART conflicts>
forbidden_gpio:  <USB D+/D-, UART0 TX/RX, strap pins>
idf_target:      esp32cX
```

**Source:** board schematic + datasheet + prior board notes in `docs/boards/`.

Never assume GPIO numbers from a related chip are identical.
Check safe_gpio against the specific board's USB and UART pin assignments.

### Step 2 — Minimal Wiring

```
Required:
  USB cable × 2   — flash port + console port
  Jumper wire × 1 — GPIO_DRIVE ↔ GPIO_INPUT (PCNT loopback)

Forbidden at this stage:
  LA probe wires, JTAG, oscilloscope probe
  (add instruments later as enhancement, not requirement)
```

Choose the PCNT jumper pair from `ael/patterns/loopback/pcnt_loopback.py`
`VALIDATED_PAIRS` if available, otherwise pick two adjacent free GPIOs and
add them to the validated list after first PASS.

### Step 3 — Canonical Test Suite

Implement tests in this fixed order.  Order matters: each layer depends on
the one below it being healthy.

| # | Tag | Layer | Wiring needed |
|---|-----|-------|--------------|
| 1 | AEL_TEMP | Internal peripheral | None |
| 2 | AEL_NVS | Flash storage | None |
| 3 | AEL_SLEEP | Power / timer | None |
| 4 | AEL_BLE | RF (low complexity) | None |
| 5 | AEL_WIFI | RF (high complexity) | None |
| 6 | AEL_PWM | GPIO peripheral output | None (self-test) |
| 7 | AEL_PCNT | Physical loopback | 1 jumper |

Output format for each tag:
```
AEL_<TAG> <detail key=value …> PASS|FAIL
AEL_SUITE_EXT DONE passed=N failed=M
```

### Step 4 — Physical Loopback (PCNT)

Use `ael/patterns/loopback/pcnt_loopback.py` to generate the C snippet:

```python
from ael.patterns.loopback.pcnt_loopback import pcnt_loopback_c_snippet
code = pcnt_loopback_c_snippet(drive_gpio=2, input_gpio=3, pulses=100)
```

Expected PASS condition: `counted == sent` (100/100).

This test proves digital GPIO output, GPIO input sampling, and real-time
timing are all working — without any external instrument.

### Step 5 — Instrument Degradation (if no LA)

| Test | With LA | Without LA |
|------|---------|-----------|
| PWM freq/duty | LA measure + range check | Driver config PASS = test PASS |
| GPIO toggle | Edge count | Omit from verdict |
| Signal timing | Cycle-accurate | Not verified |

PWM firmware self-test verdict:
```c
int ok = (timer_err == ESP_OK && chan_err == ESP_OK);
printf("AEL_PWM … %s\n", ok ? "PASS" : "FAIL");
```

### Step 6 — RF Environment Handling

Wi-Fi and BLE results are **environment-sensitive**.

```
PASS condition (always check):
  ✅ Driver initialized without error
  ✅ Scan completed without crash or timeout
  ✅ Returned data structure is valid

PASS condition (environment-dependent, do not FAIL on):
  ⚠️  ap_count == 0      (lab may have no APs)
  ⚠️  advertisers == 0   (empty RF environment)
```

For ESP32-C5 dual-band: scan both 2.4 GHz and 5 GHz separately.
Pass if either band finds ≥ 1 AP.

---

## Experiment Script

Use `experiments/templates/esp32_minimal_bringup_template.py` as the base.
Fill in:

```python
BOARD_NAME     = "esp32cX"
FIRMWARE_DIR   = "firmware/targets/esp32cX_suite_ext"
BUILD_DIR      = "artifacts/build_esp32cX_suite_ext"
FLASH_SERIAL   = "<native USB serial>"
CONSOLE_SERIAL = "<CH341 serial>"
UART_TIMEOUT_S = 35.0   # adjust for BLE scan duration
```

---

## Partition Table

BLE + Wi-Fi firmware typically exceeds the 1 MB default factory partition.
Always use the custom 1920 K partition for full-suite targets:

```csv
nvs,      data, nvs,     0x9000,   24K,
phy_init, data, phy,     0xf000,   4K,
factory,  app,  factory, 0x10000,  1920K,
```

Delete the project-level `sdkconfig` before rebuilding after changing
`sdkconfig.defaults`, otherwise the existing sdkconfig takes precedence.

---

## Cross-Board Migration

When porting from Board A to Board B (same family):

| Item | Reuse | Replace |
|------|-------|---------|
| Test structure (7 tags, order) | ✅ | — |
| UART parse / verdict logic | ✅ | — |
| Reset procedure (CH341 DTR/RTS) | ✅ | — |
| Partition table | ✅ | — |
| RF PASS logic | ✅ | — |
| `flash_serial` | — | ✅ |
| `console_serial` | — | ✅ |
| GPIO numbers (PWM, PCNT) | — | ✅ |
| `IDF_TARGET` | — | ✅ |
| Wi-Fi band API (C5 vs others) | — | ✅ if dual-band |

---

## Evidence and Benchmarks

| Board | Bring-up time | Errors | First-run result |
|-------|--------------|--------|-----------------|
| ESP32-C6 | ~5 hours | Multiple | PASS (after iteration) |
| ESP32-C5 | ~5 minutes | 0 | PASS (first run) |

The 60× speedup is the direct result of applying this pattern.

---

## Related Files

| File | Purpose |
|------|---------|
| `docs/esp32_bringup_civilization_pattern_v1.md` | Full pattern description and rationale |
| `docs/boards/esp32c6_bringup_notes.md` | C6 board-specific notes and lessons |
| `docs/boards/esp32c5_bringup_notes.md` | C5 board-specific notes and lessons |
| `experiments/templates/esp32_minimal_bringup_template.py` | Parameterized experiment runner |
| `ael/patterns/loopback/pcnt_loopback.py` | PCNT loopback C snippet generator + result parser |
| `firmware/targets/esp32c6_suite_ext/` | Reference implementation (C6) |
| `firmware/targets/esp32c5_suite_ext/` | Reference implementation (C5) |

---

## Lesson (one sentence)

> Once a board bring-up pattern is learned, it becomes a reusable civilization asset.
> New boards are no longer "projects", but "executions".
