# AEL Versioned Test Schema Specification v0.1

**Date:** 2026-03-19
**Version:** v0.1
**Status:** Draft

---

## 1. Purpose

Define a **versioned and extensible test definition model** for AEL that:

- preserves legacy tests
- enables structured new tests
- supports multiple test kinds
- allows future schema evolution

---

## 2. Core Model

Each test is interpreted under one of the following:

### 2.1 Legacy Test

A test is considered **legacy** if:

- it has no `schema_version`, OR
- `schema_version: "legacy"`

**Execution:** handled by legacy runner logic

### 2.2 Structured Test

A test is considered **structured** if:

- it declares a `schema_version` other than `legacy`

**Execution:** handled by version-aware runner

---

## 3. Required Fields (Structured Tests)

### 3.1 schema_version

```yaml
schema_version: "1.0"
```

- Identifies the test definition contract version
- Runner MUST dispatch based on this field

### 3.2 test_kind

```yaml
test_kind: "baremetal_mailbox"
```

- Defines the execution model of the test
- Determines which executor is used

### 3.3 name

```yaml
name: "stm32f103_gpio_mailbox"
```

- Unique identifier

---

## 4. Optional Fields (v1.0)

### 4.1 target

```yaml
target: "stm32f103c8t6"
```

### 4.2 labels

```yaml
labels:
  - mailbox
  - portable
  - default_candidate
```

### 4.3 supported_instruments

```yaml
supported_instruments:
  - stlink
  - esp32jtag
```

### 4.4 requires

```yaml
requires:
  mailbox: true
  datacapture: false
```

### 4.5 covers

```yaml
covers:
  - adc
  - uart
  - spi
  - exti
```

---

## 5. Execution Rules

### 5.1 Dispatch

Runner MUST follow:

1. If `schema_version` is absent → treat as `legacy`
2. If `schema_version == "legacy"` → legacy path
3. Otherwise → dispatch to version-specific handler

### 5.2 Version Handling

| schema_version | Behavior |
|----------------|----------|
| legacy | legacy execution |
| 1.0 | v1 handler |
| unknown | MUST NOT silently fallback — produce explicit error or warning |

### 5.3 test_kind Handling

Runner MUST:

- select executor based on `test_kind`
- NOT infer execution model from test name or path

---

## 6. Backward Compatibility

- All existing tests remain runnable without modification
- Absence of structured schema implies legacy behavior
- Legacy execution must remain stable

---

## 7. Design Constraints

### 7.1 No Implicit Guessing

Runner MUST NOT:

- infer mechanism from file names
- guess instrument requirements
- assume mailbox/datacapture without declaration

### 7.2 Explicit Over Implicit

Structured tests SHOULD:

- declare required capabilities
- declare supported instruments
- avoid hidden dependencies

---

## 8. Examples

### 8.1 Mailbox Test (v1.0)

```yaml
schema_version: "1.0"
test_kind: "baremetal_mailbox"
name: "stm32f103_gpio_mailbox"
target: "stm32f103c8t6"
labels:
  - mailbox
  - portable
  - cross_instrument
  - default_candidate
supported_instruments:
  - stlink
  - esp32jtag
requires:
  mailbox: true
  datacapture: false
covers:
  - adc
  - uart
  - spi
  - exti
```

Notes:
- This test is mailbox-based
- It is intended to run on both ST-Link and ESP32-JTAG
- It does not require DataCapture
- It is a candidate for cross-instrument baseline verification

### 8.2 Legacy Equivalent (Logical Form)

```yaml
schema_version: "legacy"
test_kind: "instrument_specific"
name: "stm32f103_gpio_signature"
target: "stm32f103c8t6"
supported_instruments:
  - esp32jtag
requires:
  mailbox: false
  datacapture: true
```

Notes:
- In practice, many existing legacy tests may not contain any structured schema block at all
- Missing `schema_version` is interpreted as `legacy` for compatibility

---

## 9. Evolution Policy

- Schema may evolve across versions (1.0 → 1.1 → 2.0)
- New fields must be backward-compatible within the same major version
- Breaking changes require a major version bump

### Version Roadmap (Anticipated)

| Version | Scope |
|---------|-------|
| legacy | Old tests, no structured metadata, legacy execution path |
| 1.0 | First structured schema: mechanism, labels, supported_instruments, requires |
| 1.1 | Optional enhancements: preferred_instruments, fallback_policy, verification_tier, timeouts |
| 2.0 | Richer dispatch semantics, dependency graph, test composition |

---

## 10. Test Kind Reference

Known `test_kind` values (v1.0):

| test_kind | Description |
|-----------|-------------|
| `baremetal_mailbox` | Bare-metal MCU test using Mailbox for observation |
| `instrument_specific` | Test requiring instrument-side capability (e.g. DataCapture) |

Future kinds (anticipated):

| test_kind | Description |
|-----------|-------------|
| `rtos_functional` | RTOS-based functional test |
| `linux_system` | Linux OS-level system test |
| `linux_driver` | Linux kernel driver test |
| `integration` | Multi-component integration test |

---

## 11. Guiding Principle

> Prefer structured, versioned tests for new development.
> Preserve legacy tests without modification.

---

## 12. Revision Note

This document is a **draft**.

The following may be revised in future versions:

- field names
- field meanings
- required vs optional fields
- example structures
- supported test kinds

> The examples in this document are illustrative, not final.
> The schema and example fields may be revised as AEL test coverage expands to new test kinds and execution models.

---

## 13. Summary

- Legacy tests → fallback-compatible
- Structured tests → versioned contract
- Runner → version-dispatched
- Test kinds → explicitly declared

> This enables AEL to evolve without breaking existing validation assets.
