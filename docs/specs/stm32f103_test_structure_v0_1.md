# STM32F103C8T6 Test Structure: Legacy GPIO Signature vs GPIO Mailbox

**Date:** 2026-03-19
**Version:** v0.1

## Overview

For STM32F103C8T6, there are now two independent test paths:

1. **Legacy GPIO Signature Test (ESP32-JTAG specific)**
2. **GPIO Mailbox Test (Cross-Instrument)**

These two tests are intentionally kept separate because they are based on fundamentally different validation mechanisms.

---

## 1. Legacy GPIO Signature Test

**Type:** Instrument-observed (non-mailbox)
**Instrument:** ESP32-JTAG only
**Status:** Historical / validated / preserved

### Characteristics

- Developed in the early stage of AEL
- Does **not use Mailbox**
- GPIO behavior is detected directly by the **ESP32-JTAG instrument**
- Relies on **DataCapture capability** of the instrument
- Not portable to other instruments (e.g. ST-Link)

### Role in AEL

- Represents early successful end-to-end validation
- Demonstrates **instrument-driven measurement capability**
- Serves as a **reference for ESP32-JTAG advanced features**

---

## 2. GPIO Mailbox Test (New)

**Type:** Mailbox-based / Cross-instrument
**Instruments:**
- ST-Link
- ESP32-JTAG

### Motivation

To create a **unified validation path** that can run across different instruments.

### Key Design Constraint

- **ST-Link does NOT support DataCapture**
- Therefore, the test must **not depend on GPIO waveform capture**

### What is removed

- DataCapture-based GPIO toggle verification

### What is included

The test validates functionality through Mailbox-observable behavior:

- ADC loop
- UART loop
- SPI loop
- EXTI loop

### Characteristics

- Uses **Mailbox as the observation channel**
- Fully compatible with both ST-Link and ESP32-JTAG
- Designed as a **portable baseline test**

---

## Why Two Separate Tests?

These two tests are separated because they validate the system in **different ways**:

| Aspect | Legacy GPIO Signature | GPIO Mailbox |
|--------|----------------------|--------------|
| Observation Method | Instrument (GPIO capture) | Mailbox |
| DataCapture Required | Yes | No |
| ESP32-JTAG Support | Yes | Yes |
| ST-Link Support | No | Yes |
| Portability | Low | High |
| Purpose | Instrument capability | Cross-instrument baseline |

---

## Architectural Insight

This separation introduces a **two-layer validation model**:

### 1. Instrument-Specific Validation (Upper Capability Layer)

- Uses advanced features (e.g. DataCapture)
- Higher observability
- Lower portability

### 2. Mailbox-Based Validation (Portable Baseline Layer)

- Works across instruments
- Lower dependency on hardware features
- Acts as a **standard regression path**

---

## Conclusion

For STM32F103C8T6:

- The **Legacy GPIO Signature test** is preserved as an ESP32-JTAG-specific validation path.
- The **GPIO Mailbox test** is introduced as a new, portable, cross-instrument validation path.

Together, they form a complementary system:

> Legacy tests explore instrument capabilities, while Mailbox tests establish a unified baseline.
