# Instrument Roles and Limits v0.1

## Purpose
This document defines the primary role, technical strengths, realistic limitations, and the recommended "first-stage" use for each instrument supported by AEL.

Use this as the source of truth for the **[Instrument Role]** and **[Constraint Statement]** sections of the AEL Response Policy.

---

## 1. ST-Link
- **Primary Role**: Flash & Debug Interface.
- **Strengths**: 
  - Direct SWD/JTAG access to Cortex-M targets.
  - High-speed flashing.
  - Reliable GDB/OpenOCD/st-util integration for memory inspection.
- **Limits**:
  - **No GPIO signal capture**: Cannot verify pin toggling frequency, PWM, or digital logic states externally.
  - **No stimulus generation**: Cannot act as a signal generator for DUT inputs.
- **Best First-Stage Use**: **Mailbox Verification**. Verify that the firmware has started by reading a "heartbeat" or "ready" variable from a specific RAM address via GDB.

---

## 2. esp32jtag
- **Primary Role**: HIL (Hardware-in-the-Loop) Master Instrument.
- **Strengths**:
  - **Integrated Logic Capture**: Can capture and verify GPIO signals (frequency, duty cycle, pulse count).
  - **Multi-domain Verification**: Supports Digital (GPIO), Analog (ADC), and Communication (UART/I2C/SPI) loopback.
  - **Remote Access**: Connects via WiFi/Network, allowing for a headless lab setup.
- **Limits**:
  - Lower SWD/JTAG speed compared to dedicated local probes like ST-Link.
  - Relies on network stability for real-time monitoring.
- **Best First-Stage Use**: **GPIO Signature Verification**. Verify that the target is alive by capturing a unique frequency signature on a designated pin.

---

## 3. USB-UART Bridge
- **Primary Role**: Log Monitor & Serial Terminal.
- **Strengths**:
  - Direct access to `printf` / `printk` logs.
  - Simple, low-cost integration for basic "alive" checks.
- **Limits**:
  - **No Debug Control**: Cannot reset, halt, or inspect the MCU's internal memory/registers.
  - **No Signal Verification**: Cannot verify any non-UART hardware behavior.
- **Best First-Stage Use**: **Boot Log Verification**. Scan for a specific "Boot Success" or "Hello World" string in the serial output.

---

## 4. Summary Table

| Instrument | Best For | Verification Method | Capture Capability |
|---|---|---|---|
| **ST-Link** | Local dev, high-speed flash | Mailbox (RAM) | None |
| **esp32jtag** | Automated HIL, remote lab | GPIO/ADC Capture | High (Digital/Analog) |
| **USB-UART** | Basic monitoring | Text Pattern Matching | UART only |
