# HIL Automated Verification v0.1

## Purpose
This document defines the protocols and methods for **Hardware-in-the-Loop (HIL)** verification in AEL. It provides a standardized way to determine if a DUT (Device Under Test) is behaving as expected based on real-time evidence.

## 1. Verification Methods

### A. Mailbox (Debug Surface)
- **Concept**: Reading/writing specific RAM addresses via the debug interface (SWD/JTAG).
- **Protocol**: 
  - The firmware writes a "Ready" marker (e.g., `0xAEL1`) to a fixed address.
  - The agent reads this address via GDB.
- **Best For**: "Step 0" bring-up, verifying successful boot, and checking internal state.
- **Reference**: `docs/specs/ael_mailbox_contract_v0_1.md`.

### B. GPIO Capture (Digital Surface)
- **Concept**: Measuring physical signal parameters (frequency, duty cycle, pulse count) using an instrument.
- **Protocol**: 
  - The instrument (e.g., `esp32jtag`) captures a stream of pulses on a designated pin.
  - The `verification_model.py` compares the measured frequency against the expected frequency (within a tolerance).
- **Best For**: Verifying peripheral initialization (TIM/PWM) and basic logic toggling.

### C. ADC/Analog Loopback (Analog Surface)
- **Concept**: Generating an analog voltage (DAC) or measuring an input (ADC) across a loopback connection.
- **Best For**: Verifying analog front-ends and ADC accuracy.

### D. UART/Loopback Communication (Communication Surface)
- **Concept**: Sending a unique text pattern through a UART and verifying its correct reception at the other end.
- **Best For**: Verifying serial communication stacks.

---

## 2. Verification Levels

| Level | Name | Description | Required Instrument |
|---|---|---|---|
| **L0** | **Boot Smoke** | Mailbox-only. Proves MCU is powered, flashed, and running. | ST-Link or esp32jtag |
| **L1** | **Pulse Smoke** | Proves at least one pin is toggling at a specific freq. | esp32jtag |
| **L2** | **Full Functional** | Multiple signals (UART, SPI, ADC) verified. | esp32jtag + Loopback wiring |

---

## 3. Dealing with Measurement Tolerance
HIL verification must account for real-world drift (clock inaccuracy, network latency).
- **Frequency Tolerance**: Default ±5% for internal RC oscillators; ±0.1% for external crystals.
- **Settle Time**: Allow 1–4 seconds for the hardware to stabilize after a reset/flash before beginning measurement.
