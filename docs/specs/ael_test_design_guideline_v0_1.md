# AEL Test Design Guideline v0.1

**Date:** 2026-03-19
**Version:** v0.1
**Scope:** Embedded validation tests in AEL

---

## Purpose

This document defines the **standard methodology for designing tests in AEL**.

The goal is to ensure:

- Cross-instrument compatibility
- High reliability and reproducibility
- Clear separation of responsibilities between firmware and instrument
- Scalable validation across multiple boards and instruments

---

## Core Principle

> **Prefer mailbox-based validation by default.
> Use instrument-specific validation only when necessary.**

---

## Two-Layer Test Architecture

AEL tests are divided into two fundamental layers:

### 1. Mailbox-Based Tests (Portable Baseline)

**Default choice for all new tests**

#### Characteristics

- Use **Mailbox as the observation channel**
- Do NOT depend on instrument-specific capabilities
- Fully portable across different instruments:
  - ST-Link
  - ESP32-JTAG
  - Future instruments

#### Advantages

- High portability
- Stable regression baseline
- Easy to scale across boards
- Minimal hardware dependency

#### Typical Use Cases

- Functional validation
- Peripheral loop tests: ADC, UART, SPI, EXTI
- Bring-up baseline verification

---

### 2. Instrument-Specific Tests (Capability Layer)

**Used only when mailbox is insufficient**

#### Characteristics

- Depend on **instrument-side capabilities**
- Examples:
  - GPIO waveform capture (DataCapture)
  - High-speed sampling
  - External stimulus generation

#### Advantages

- Higher observability
- Enables advanced validation scenarios

#### Limitations

- Not portable across instruments
- Higher maintenance cost
- Requires specific hardware support

#### Typical Use Cases

- Signal integrity validation
- Timing verification
- Hardware-level debugging
- High-speed data capture

---

## Design Decision Rule

When designing a new test, follow this decision flow:

### Step 1 — Can this be verified via Mailbox?

- YES → Use Mailbox test
- NO → go to Step 2

### Step 2 — Is instrument capability required?

- YES → Use instrument-specific test
- NO → Redesign test (avoid unnecessary dependency)

---

## Compatibility Rule

> A test intended as a **default or regression test MUST be mailbox-based.**

This ensures:

- It can run on all supported instruments
- It becomes part of the **global validation baseline**

---

## Naming Convention

Tests should clearly reflect:

- Target MCU / board
- Function
- Mechanism (mailbox vs instrument)

### Recommended format

```
<target>_<function>_<mechanism>
```

### Examples

- `stm32f103_gpio_mailbox`
- `stm32f103_gpio_signature` (legacy / instrument-based)
- `esp32c6_adc_mailbox`
- `rp2040_spi_mailbox`

---

## Stability Principle

> **Do not modify validated tests.
> Create new tests instead.**

### Rationale

- Preserves historical validation integrity
- Avoids regression ambiguity
- Enables comparison across generations

### Example

- Old: `gpio_signature` — keep unchanged
- New: `gpio_mailbox` — new independent test

---

## Architectural Insight

AEL validation evolves along two axes:

| Layer | Role |
|-------|------|
| Mailbox Layer | Standard baseline (portable, scalable) |
| Instrument Layer | Capability extension (powerful, specialized) |

Together:

> **Mailbox defines consistency.
> Instrument defines capability ceiling.**

---

## Future Direction

- Expand mailbox-based coverage across all MCU families
- Gradually unify default verification paths under mailbox
- Use instrument-specific tests as **optional enhancement layers**
- Enable parallel large-scale validation using mailbox baseline

---

## Summary

- Mailbox tests are the **default foundation**
- Instrument tests are **optional extensions**
- Keep them **separate, explicit, and intentional**

> This structure ensures AEL remains both **portable and powerful**.
