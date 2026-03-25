# ESP32 Bring-Up & Test Architecture Rule
## (No-Wire Console-First + One Test, One Program)

---

## 1. Overview

This document defines the mandatory bring-up methodology and test architecture for all
ESP32-family boards (ESP32, S2, S3, C3, C5, C6, P4, etc.).

It combines two critical engineering rules:

1. **No-Wire Console-First Validation**
2. **One Test, One Program**

These rules are REQUIRED for all board validation, Golden Test Packs, and AEL execution
pipelines.

---

## 2. Core Principles

### Principle 1 — Reduce Variables First

> Always validate the system in the simplest possible configuration before introducing
> additional complexity.

---

### Principle 2 — Isolate Failures

> Each test must be independently executable and must not depend on side effects from
> other tests.

---

### Principle 3 — Stage by Dependency

> Tests must be ordered from lowest dependency (no wiring) to highest dependency
> (external integration).

---

## 3. Rule A — No-Wire Console-First Validation

### Requirement

Before running any test, the board MUST pass a minimal console output program under
**no external wiring condition**.

---

### Stage 0 — Bare Board Validation (NO WIRES)

**Condition:**
- No jumpers
- No DUT connections
- Only power + programming interface

**Program Requirement:**

A minimal program that prints a deterministic string.

**Example:**
```
HELLO_AES channel=UART0
HELLO_AES channel=USB_CDC
HELLO_AES channel=USB_SERIAL_JTAG
```

**Must PASS:**
- Flash success
- Reliable boot
- Correct console output
- Repeatable across resets

---

### Stage 1 — No-Wire Functional Tests

Still **no external wiring**.

Examples:
- NVS
- Temperature
- Timers
- Wi-Fi / BLE
- Sleep
- On-board LED

---

### Stage 2 — Wiring / Integration Tests

External connections allowed.

Examples:
- UART to DUT
- SPI / I2C
- JTAG routing
- External GPIO interaction

---

### Invariant

> No board bring-up is valid unless Stage 0 (no-wire console) passes first.

---

## 4. Rule B — One Test, One Program

### Requirement

> Each test MUST be implemented as an independent program or independently runnable unit.

---

### Forbidden Pattern ❌

```c
main() {
    test_nvs();
    test_wifi();
    test_ble();
    test_spi();
    test_uart();
    ...
}
```

This is NOT allowed.

---

### Required Pattern ✅

Each test is independent:

- `hello_uart0`
- `hello_usb`
- `test_nvs`
- `test_temp`
- `test_wifi`
- `test_ble`
- `test_sleep`
- `test_uart_link`
- `test_spi_fpga`
- `test_i2c_device`

Each must:
- Compile independently
- Flash independently
- Run independently
- Produce its own PASS/FAIL result

---

### Rationale

Monolithic test programs cause:
- State contamination between tests
- Hidden dependencies
- Hard-to-debug failures
- Non-reproducible issues
- Longer debug cycles

---

## 5. Combined Execution Model

Correct workflow:

1. **Stage 0**
   - Run minimal hello program
   - Verify console output

2. **Stage 1**
   - Run each no-wire test independently

3. **Stage 2**
   - Add wiring
   - Run each integration test independently

---

## 6. AEL / Automation Enforcement

This rule must be enforced as a **hard gate**:

### Preflight Gate:

- Minimal flash → PASS
- Minimal boot → PASS
- Console output → PASS

Otherwise:
→ STOP execution

---

### Execution Model:

- Run tests one by one
- No shared `main()`
- No chained execution

---

## 7. Anti-Pattern Warning

> Do NOT apply "convenience-driven software patterns" to embedded bring-up.

In software:
- Combining tests may reduce code duplication

In embedded systems:
- Combining tests **increases failure coupling**
- Makes hardware debugging significantly harder

---

## 8. Refactoring Requirement (MANDATORY)

If an existing implementation:
- Combines multiple tests into a single program
- Runs all tests inside one `main()`

Then it MUST be refactored.

---

### Required Refactor Actions:

1. Extract each test into its own program:
   - One test = one entry point

2. Remove all cross-test dependencies

3. Ensure each test:
   - Initializes hardware independently
   - Cleans up its own state
   - Does not rely on previous tests

4. Reorganize into staged structure:
   - hello
   - no-wire tests
   - wiring tests

---

## 9. Summary

> Embedded bring-up is not about "doing everything at once".
> It is about **controlling variables and isolating failures**.

Correct approach:
- No-wire first
- Console first
- One test at a time
- Stage by dependency

---

## 10. Short Name

**ESP32 Staged Bring-Up + Isolated Test Rule**

or

**No-Wire First + One-Test-Per-Program Rule**
