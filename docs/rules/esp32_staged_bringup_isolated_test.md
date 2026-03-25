# ESP32 Bring-Up & Test Architecture Rule (Unified)
## No-Wire Console-First + One Test Per Program + Staged Suites + Optional Full Suite

---

## 1. Overview

This document defines the mandatory bring-up methodology and test architecture for all
ESP32-family boards (ESP32, S2, S3, C3, C5, C6, P4, etc.).

It unifies four core rules:

1. **No-Wire Console-First Validation**
2. **One Test, One Program**
3. **Stage by Dependency**
4. **Optional Full Board Suite (Built on Verified Tests Only)**

These rules are REQUIRED for all board validation, Golden Test Packs, and AEL execution
pipelines.

---

## 2. Core Philosophy

> Embedded systems must prioritize **controllability, observability, and debuggability**
> over convenience.

Unlike general software systems, embedded bring-up interacts with physical hardware and
must strictly control variables.

---

## 3. Rule A — No-Wire Console-First Validation

### Requirement

Before any functional testing, the board MUST pass a minimal console output program under
**no external wiring condition**.

---

### Stage 0 — Bare Board Validation (NO WIRES)

**Condition:**
- No jumpers
- No DUT connections
- Only power + programming interface

**Program Requirement:**

A minimal program that prints a deterministic string to the console interface.

**Example:**
```
HELLO_AES channel=UART0
HELLO_AES channel=USB_CDC
HELLO_AES channel=USB_SERIAL_JTAG
```

**Must PASS:**
- Flash succeeds
- Board boots reliably
- Console output is visible
- Output is repeatable across resets

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
- UART link
- SPI / I2C
- JTAG routing
- External GPIO

---

### Invariant

> No board bring-up is valid unless Stage 0 passes first.

---

## 4. Rule B — One Test, One Program

### Requirement

> Each test MUST be independently executable.

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

---

### Required Pattern ✅

Each test is independent:

- `hello_uart0`
- `test_nvs`
- `test_temp`
- `test_wifi`
- `test_ble`
- `test_sleep`
- `test_uart`
- `test_spi`
- `test_i2c`

Each must:
- Build independently
- Flash independently
- Run independently
- Produce its own PASS/FAIL result

---

### Rationale

Monolithic tests cause:
- State contamination between tests
- Hidden dependencies
- Hard-to-debug failures
- Non-reproducible issues

---

## 5. Rule C — Stage by Dependency

Tests must follow this order:

1. Minimal console (no wire)
2. No-wire functional tests
3. Wiring / integration tests

This ordering ensures that when a test fails, the problem space is already bounded by what
passed before it.

---

## 6. Rule D — Optional Full Board Suite (ALLOWED WITH CONSTRAINTS)

A full board test suite is **allowed and recommended**, but ONLY under strict conditions.

---

### Purpose

- Fast board health check
- Regression testing
- Manufacturing / field validation
- Golden Test execution shortcut

---

### Critical Requirement

> The full suite MUST be built on already validated independent tests.

Independent tests are validated first. The full suite is added afterward — never before.

---

### Allowed Structure

The full suite acts as an **orchestration layer**, not a reimplementation.

---

### Strongly Recommended Model — External Runner Orchestration (Best)

```
flash hello_uart0  → verify PASS
flash test_nvs     → verify PASS
flash test_wifi    → verify PASS
flash test_spi     → verify PASS
...
```

This is the AEL pack model. Each test remains a separate program. The runner flashes and
verifies each in sequence. Truth layer and convenience layer are identical.

---

### Acceptable Model — Combined Firmware (With Care)

A single combined firmware MAY exist, but it MUST:

- Clearly separate each sub-test as an independent function
- Print PASS/FAIL per sub-test
- Avoid shared hidden state between sub-tests
- Reinitialize hardware within each sub-test function
- NOT depend on execution-order side effects

---

### Forbidden ❌

Rewriting all tests into a single large `main()` with shared logic, shared state, and
hidden coupling between test steps.

---

## 7. Truth Layer vs Convenience Layer

> Independent tests are the **truth layer**.
> Full suites are the **convenience layer**.

The system MUST always preserve:
- Ability to run each test individually
- Ability to debug at single-test granularity

The full suite is a time-saving shortcut. It does NOT replace individual tests.

---

## 8. AEL / Automation Enforcement

### Preflight Gate

Before any test pack execution:

- Minimal flash → PASS
- Minimal boot → PASS
- Console output → PASS

Otherwise: → STOP

---

### Execution Model

- Tests run independently (or as cleanly separated functions in the combined firmware)
- No chained hidden execution
- Failures must be localizable to a single test

---

## 9. Mandatory Refactoring Rule

If an existing implementation:
- Combines multiple tests in one program with a single `main()`
- Has shared state or hidden dependencies between test steps

Then it MUST be refactored.

---

### Required Refactor Actions

1. Split into independent test programs (one per test)
2. Ensure no cross-test dependency
3. Reorganize into staged structure:
   - hello (Stage 0)
   - no-wire tests (Stage 1)
   - wiring tests (Stage 2)
4. Optionally add full board suite AFTER all individual tests are validated

---

## 10. Key Engineering Insight

> Embedded debugging is about **reducing variables and isolating failures**.

NOT about:
- Minimizing code duplication
- Maximizing convenience

In software: combining tests may reduce code.
In embedded: combining tests **increases failure coupling** and makes hardware debugging
significantly harder.

---

## 11. Correct Workflow

```
1. No wiring
2. Flash + run minimal hello → PASS
3. Flash + run each no-wire test independently → PASS each
4. Add wiring
5. Flash + run each integration test independently → PASS each
6. (Optional) Run full board suite as convenience shortcut
```

---

## 12. Short Name

**ESP32 Staged Bring-Up + Isolated Test + Full Suite Rule**

or

**No-Wire First + One-Test-Per-Program + Verified Full Suite**
