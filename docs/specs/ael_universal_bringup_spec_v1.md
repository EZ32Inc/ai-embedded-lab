# AEL Universal Bring-up & Brownfield Migration Spec v1

## 1. Purpose

This document defines a universal method for bringing an existing working system under AEL (AI Embedded Lab) management.

A "brownfield system" is any system that already works manually, including:
- MCU firmware projects
- FPGA designs
- Linux-based systems
- Hybrid systems (MCU + FPGA, SoC, etc.)

The goal is NOT to redesign the system, but to:
- Understand it
- Align with the user
- Take control of its execution loop
- Automate and extend it

---

## 2. Core Principle

All AEL onboarding follows:

**Discovery → Hypothesis → Confirmation → Execution → Verify → Explore**

This is mandatory.

AEL must:
- Read and infer from the system first
- Form structured understanding
- Ask for confirmation (not raw questioning)
- Then execute

This is a **co-discovery process between user and AI**.

---

## 3. Generalized Control Loop

The minimal control loop is:

**Build → Deploy → Observe → Verify**

| Step     | Meaning |
|----------|--------|
| Build    | Generate executable artifact (binary/bitstream/image) |
| Deploy   | Load artifact to system |
| Observe  | Get system behavior (log/signal/state) |
| Verify   | Determine correctness |

AEL does not depend on system type — only on whether this loop exists.

---

## 4. Domain Mapping Examples

### MCU (ESP32 / STM32)
- Build → compile firmware
- Deploy → flash via USB/JTAG
- Observe → UART/USB log
- Verify → functional test / API

### FPGA
- Build → synthesize bitstream
- Deploy → JTAG/SPI load
- Observe → logic analyzer / GPIO
- Verify → waveform / loopback

### Linux System
- Build → kernel + rootfs
- Deploy → SD/eMMC/TFTP
- Observe → serial console / network
- Verify → service/API

### Hybrid (MCU + FPGA)
- Combined loops
- Cross-validation (e.g., loopback)

---

## 5. Migration Process

### Step 1 — Discovery
AEL inspects:
- source code
- build scripts
- environment
- hardware features

### Step 2 — Hypothesis
AEL infers:
- build method
- deploy method
- observe path
- verify method

### Step 3 — Confirmation
User confirms or corrects:
- build path
- deploy path
- verify path

### Step 4 — Execution
AEL automates:
- build
- deploy
- observe

### Step 5 — Verify
AEL validates system behavior.

### Step 6 — Explore
AEL can:
- run experiments
- perform loopback
- explore configurations

---

## 6. Knowledge Layers

### Board / Project-Specific
- FPGA features
- wiring / loopback
- board quirks

### Family / Platform-Specific
- ESP32 / STM32 patterns
- USB vs UART reset behavior
- SDK/toolchain usage

### AEL-Core
- migration method
- control loop abstraction

### Not Stored
- private source code
- temporary debugging noise

---

## 7. Key Insight

> AEL does not care what the system is.
> It only cares whether a controllable loop exists.

---

## 8. Exploration Capability

Once the loop is established, AEL can:
- auto-generate tests
- run loopback validation
- search parameter space
- discover optimal configurations

---

## 9. Example: ESP32JTAG

- MCU: ESP32-S3 (family knowledge)
- FPGA: logic analyzer + GPIO routing (board-specific)
- Loopback: Port D → Port A (self-validation)
- Web UI + API (observe/verify path)

---

## 10. Summary

AEL onboarding = establishing control.

Once Build / Deploy / Observe / Verify is automated,
the system is under AEL control and can evolve.
