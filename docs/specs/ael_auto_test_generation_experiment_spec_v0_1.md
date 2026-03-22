# AEL Auto-Test Generation Experiment Spec v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. Experiment Purpose

This experiment validates AEL's ability to act as a real **test architect** rather than a test executor:

> Given a board, DUT, and available instruments with a minimal-wiring constraint — can AEL automatically derive the set of tests that should be run, explain the required wiring, and rank them by cost?

This is a higher-level capability test than "run a specific test." It tests AEL's reasoning about the problem before execution.

---

## 2. What Is Actually Being Tested

This experiment tests **four distinct capabilities**:

### Capability 1 — Test Generation
Not hand-picking tests, but having AEL automatically derive from DUT features and instrument capabilities which tests can be generated.

### Capability 2 — Minimal Wiring Reasoning
AEL must not just say "what can be tested" but also:
- This test requires zero extra wiring
- This test requires one jumper wire
- This test requires an external signal source (not recommended currently)

### Capability 3 — Onboard Instrument Utilization
AEL must recognize that onboard instruments are already connected (wiring cost ≈ 0) and prioritize paths that use them.

### Capability 4 — Test Ranking
Not just a flat list — AEL must rank by value: smallest wiring cost, highest coverage, best use of available resources.

---

## 3. Target Setup

### Board

**ESP32-S3 DevKit** or **ESP32-C6 DevKit**

### DUT

`esp32s3_main` (or `esp32c6_main`) — the main MCU

### Available Instruments (both onboard)

| ID | Type | Location |
|----|------|----------|
| `usb_uart_bridge` | USB-to-UART bridge chip (e.g., CP2102) | onboard |
| `usb_serial_jtag` | ESP32 built-in USB Serial/JTAG | onboard |

### Objective

> Generate the maximum number of runnable tests under the minimum wiring constraint.

---

## 4. Input to AEL

```
I have an ESP32-S3 (or ESP32-C6) development board.
This board has two onboard instruments:
  - USB-to-UART bridge (onboard)
  - USB Serial/JTAG interface (onboard)

Please automatically generate the maximum number of executable tests
under the minimum wiring constraint.

For each test, provide:
  - Test name
  - Target DUT capability
  - Firmware template category
  - Selected instrument
  - Extra wiring required
  - Wiring cost
  - Verification level
  - Blocked reason (if not runnable)
```

---

## 5. Expected Output Format

```
Board: esp32s3_devkit
DUT: esp32s3_main
Available instruments:
  - usb_uart_bridge (onboard)
  - usb_serial_jtag (onboard)

Generated tests:

1. USB UART Console Smoke Test
   Instrument: usb_uart_bridge
   Extra wiring: none
   Wiring cost: 0
   Reason: onboard UART path already available

2. USB Serial/JTAG Console Smoke Test
   Instrument: usb_serial_jtag
   Extra wiring: none
   Wiring cost: 0
   Reason: onboard USB Serial/JTAG available

3. Flash via USB-UART
   Instrument: usb_uart_bridge
   Extra wiring: none
   Wiring cost: 0

4. Flash via USB Serial/JTAG
   Instrument: usb_serial_jtag
   Extra wiring: none
   Wiring cost: 0

5. GPIO Output Smoke Test
   Instrument: usb_uart_bridge or usb_serial_jtag
   Extra wiring: 1 loopback jumper (GPIO_OUT → GPIO_IN)
   Wiring cost: 2

6. GPIO Loopback Test
   Instrument: usb_uart_bridge or usb_serial_jtag
   Extra wiring: 1 loopback jumper
   Wiring cost: 2

7. UART Loopback Test
   Instrument: usb_uart_bridge or usb_serial_jtag
   Extra wiring: TX→RX loopback
   Wiring cost: 2

8. PWM Capture Test
   Instrument: usb_uart_bridge or usb_serial_jtag
   Extra wiring: GPIO_PWM → LA_CH0
   Wiring cost: 2

9. ADC Smoke Test (internal reference)
   Instrument: usb_uart_bridge or usb_serial_jtag
   Extra wiring: none (uses internal VCC/GND reference)
   Wiring cost: 0

10. ADC External Signal Test
    Instrument: usb_uart_bridge or usb_serial_jtag
    Extra wiring: external signal source → ADC pin
    Wiring cost: 10 (requires new instrument)

11. I2C Bus Scan
    Instrument: usb_uart_bridge or usb_serial_jtag
    Extra wiring: pull-up resistors if not onboard
    Wiring cost: 1–3

...

Blocked / not generated:
  - Current consumption test
    Missing: current measurement instrument

  - Deep JTAG debug test
    AEL status: future / not yet supported
```

---

## 6. Wiring Cost Model

| Situation | Cost |
|-----------|------|
| Onboard instrument, already connected | 0 |
| External USB cable only | 1 |
| 1 jumper wire | 2 |
| Multiple jumper wires | 5 |
| Requires new external instrument | 10 |

**Optimization goal:** `maximize test coverage` subject to `minimum wiring cost`

---

## 7. Core Principles for Test Generation

### P1 — Two instruments are two access paths, not two test systems

`usb_uart_bridge` and `usb_serial_jtag` are both access paths to the same DUT (`esp32s3_main`). They share the same firmware model and test family. AEL must not generate separate test suites for each instrument.

### P2 — Test generation starts from DUT capabilities, not instrument types

Correct order:
1. Identify what capabilities the DUT has (GPIO, PWM, ADC, UART, I2C, SPI, ...)
2. Enumerate test families that match those capabilities
3. Filter by which tests are feasible given available instruments and wiring
4. Rank by wiring cost

**Wrong order:** "I have a USB-UART bridge, therefore generate UART tests."

### P3 — Instrument path is execution binding, not test definition

The test family (what to test) is defined by DUT capabilities.
The instrument (how to execute) is bound at execution time.
These two are separate concerns.

### P4 — Prioritize zero extra wiring tests

Tests that can run with zero extra wiring using already-available onboard instruments should be ranked first.

### P5 — Same DUT, same firmware template family

Both instruments drive the same DUT firmware. AEL should not create two separate firmware stacks for the same DUT just because there are two instruments.

### P6 — Output must include wiring explanation

AEL output must not be just a list of test names. It must include:
- Which instrument is selected
- What extra wiring is required
- Why that instrument was selected

### P7 — Honestly report blocked tests

Good AEL output explicitly categories tests as:
- `executable_now` — zero or minimal wiring, instrument available
- `executable_with_minor_wiring` — small additional connections needed
- `blocked_missing_instrument` — requires instrument not available
- `blocked_unsupported` — not yet implemented in AEL

---

## 8. Expected Test Families to Generate

AEL should be able to generate tests across these peripheral families (not limited to USB/console tests):

| Family | Zero-wire possible? | Notes |
|--------|-------------------|-------|
| Console smoke test | Yes | Via both instruments |
| Flash / boot | Yes | Via both instruments |
| GPIO output | With loopback | 1 jumper |
| GPIO input | With loopback | 1 jumper |
| GPIO loopback | Yes (loopback) | 1 jumper |
| PWM output + capture | With loopback or LA | 1 connection |
| ADC smoke test | Yes | Internal reference |
| ADC accuracy test | With signal source | External instrument |
| UART loopback | Yes (loopback) | TX→RX |
| I2C bus scan | Yes (if pull-ups onboard) | |
| SPI loopback | With loopback | 2 wires |
| Current consumption | No | Requires current meter |

---

## 9. Validation Criteria

| Criterion | Pass |
|-----------|------|
| Board/DUT/instrument correctly separated | Board ≠ DUT |
| Two instruments recognized as two access paths | Not two test systems |
| Tests generated from DUT capabilities | Not from instrument types |
| Zero-wire tests ranked first | Clear wiring cost ordering |
| Wiring explanation provided per test | Not just test names |
| Blocked tests explicitly called out | With reasons |
| ADC / PWM / GPIO / I2C families present | Not limited to console/flash |

---

## 10. Two-Round Verification Protocol

### Round 1 — Learning Round (ESP32-S3)
Goal: identify gaps, fix planner, get first correct output.

### Round 2 — Transfer Validation Round (ESP32-C6 or different board)
Goal: verify that AEL applies the correct principles to a **similar but different** board without re-teaching.

Round 2 passes if AEL:
- Still correctly separates Board / DUT / Instrument
- Still recognizes dual instruments as two access paths
- Still generates from DUT capabilities
- Still applies minimal-wiring ranking
- Does not blindly copy Round 1 results (generalizes, not memorizes)

---

*Extracted from AEL design discussion. Companion docs: `ael_board_dut_definition_spec_v0_1.md`, `ael_experiment_methodology_v0_1.md`*
