# AEL Board / DUT Definition Spec v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. Core Principle

> **A board is not a DUT.**
> A board is the physical assembly that may host one or more DUTs and one or more instruments.
>
> Therefore, onboard presence does not imply DUT identity.

This is a foundational definition that must be formalized in AEL. As boards grow more complex — multi-MCU designs, boards with onboard debug probes, boards with integrated USB-UART bridges — the old implicit assumption "board = DUT" causes increasing confusion.

---

## 2. Canonical Object Definitions

### Board

> A physical assembly that hosts one or more DUTs and zero or more instruments.

Board is the container / carrier. It is not itself the device under test.

### DUT (Device Under Test)

> The target device being tested, programmed, verified, or debugged.

DUT identity is defined by **role** (being tested), not by physical location.

### Instrument

> An object that provides connection, observation, control, programming, debugging, or measurement capabilities for a DUT.
> An instrument may be located on the board or outside the board.

Instrument identity is defined by **capability role**, not by physical location.

---

## 3. Key Relationships

```
board contains dut(s)
board contains instrument(s)
instrument serves dut
test applies to dut
test uses instrument
```

A board can contain:
- 1 DUT (most common case: single-MCU devkit)
- Multiple DUTs (multi-MCU boards)
- 0 or more instruments (onboard bridges, debuggers, power monitors)

---

## 4. The ESP32-S3 / C6 Case Study

Many ESP32-S3 and ESP32-C6 development boards expose two USB interfaces:

1. **Board-mounted USB-UART bridge** (e.g., CP2102, CH343)
   - A separate chip on the board
   - Provides a serial console / download path
   - Not part of the main MCU

2. **DUT-integrated USB Serial/JTAG controller**
   - Built into the ESP32-S3/C6 silicon
   - Provides: CDC serial console, flash programming, JTAG debug
   - Is physically part of the DUT itself, but exposes instrument-like capabilities to the host

Under the old "board = DUT" model, these two interfaces are confusing to categorize.

**Under the new model:**

```yaml
board:
  id: esp32s3_devkit

duts:
  - id: esp32s3_main
    type: esp32s3

instruments:
  - id: usb_uart_bridge
    type: usb_uart_bridge
    location: onboard
    targets:
      - esp32s3_main

  - id: usb_serial_jtag
    type: usb_serial_jtag
    location: onboard
    targets:
      - esp32s3_main
```

Both instruments serve the same DUT. They are two access paths to the same target — not two independent test systems.

---

## 5. Two Instrument Location Types

Instrument `location` field:

| Value | Meaning |
|-------|---------|
| `onboard` | Physically on the board (board-mounted bridge, onboard debugger, DUT-integrated endpoint) |
| `external` | External device connected to the board via cable or probe |

> **Note:** Both `onboard` and `external` instruments are first-class instruments in AEL. Their logic is the same; only their physical location differs.

### Examples by Location

**External instruments:**
- ST-Link, J-Link
- External USB-UART bridge cable
- Benchtop multimeter, oscilloscope
- ESP32-based meter instrument

**Onboard instruments:**
- CP2102 / CH343 / FTDI bridge chips on devkits
- Onboard ST-Link on Nucleo / Discovery boards
- CMSIS-DAP on LaunchPad boards
- ESP32-S3/C6 internal USB Serial/JTAG

---

## 6. Multi-MCU Board Example

A board with a primary MCU (DUT) and an auxiliary ESP32-S3 acting as a bridge:

```yaml
board:
  id: custom_board_v1

duts:
  - id: primary_mcu
    type: stm32f407

instruments:
  - id: aux_esp32s3_bridge
    type: esp32s3_uart_bridge
    location: onboard
    targets:
      - primary_mcu

  - id: stlink_onboard
    type: stlink
    location: onboard
    targets:
      - primary_mcu
```

---

## 7. Two Confusions to Avoid

### Confusion 1: Treating the entire board as the DUT

This causes all onboard bridge chips, debuggers, and auxiliary MCUs to have unclear identities.

**Resolution:** Board is the container. DUT is what is being tested. These are different things.

### Confusion 2: Treating "onboard" as "belongs to DUT"

"Onboard" only describes physical location. Whether something is a DUT depends on whether it is the test target — not where it is physically located.

---

## 8. Minimal Implementation Changes

To implement this spec, the minimum required changes are:

### 8.1 Board Schema

Explicitly separate `duts` and `instruments` at the top level of board configs:

```yaml
board:
  id: <board_id>
  name: <board_name>

duts:
  - id: <dut_id>
    type: <chip_type>
    ...

instruments:
  - id: <instrument_id>
    type: <instrument_type>
    location: onboard | external
    targets:
      - <dut_id>
    ...
```

### 8.2 Instrument Location Field

Add a `location` field to instrument definitions:
- `onboard` — physically on the board
- `external` — connected externally

### 8.3 Connection Relationships (Optional Enhancement)

When needed, add explicit connection relationships:

```yaml
connections:
  - subject: usb_uart_bridge
    predicate: connected_to
    object: esp32s3_main.uart0

  - subject: usb_serial_jtag
    predicate: embedded_in
    object: esp32s3_main
```

---

## 9. Impact on Test Planning

Once Board and DUT are properly separated:

- `test applicability` checks against `dut`, not `board`
- Instrument selection considers all available instruments (both onboard and external)
- Multiple instruments targeting the same DUT are recognized as **alternative access paths**, not separate test systems
- Same test family / firmware can be run via different instrument paths (see `ael_auto_test_generation_experiment_spec_v0_1.md`)

---

## 10. Formal Principle Statements

The following sentences are suitable for inclusion in the AEL formal spec:

> **P1.** A board is not itself the DUT. A board is the physical assembly that may host one or more DUTs and one or more instruments.

> **P2.** Onboard presence does not imply DUT identity.

> **P3.** Instrument is defined by the capabilities it provides to testing, control, observation, programming, or debugging workflows — not by whether it is physically external to the DUT.

> **P4.** An instrument may be external, board-mounted, or integrated into the DUT, as long as it exposes usable endpoints to the host/test runtime.

> **P5.** Multiple instruments targeting the same DUT are alternative access paths, not independent test systems.

---

*Extracted from AEL design discussion. Companion docs: `ael_compatibility_mapping_spec_v0_1.md`, `ael_auto_test_generation_experiment_spec_v0_1.md`*
