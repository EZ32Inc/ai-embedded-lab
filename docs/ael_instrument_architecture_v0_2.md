
# AEL Instrument Architecture Guideline v0.2
AI-Compatible Instrument Ecosystem Design

Author: AEL Project
Status: Draft
Purpose: Define principles for designing AEL-compatible instruments

---

# 1. Introduction

AEL (Autonomous Embedded Lab) enables AI agents to automatically develop, test, and validate firmware on real hardware.

In this model:

- Humans connect hardware
- AI discovers instruments
- AI runs experiments
- AI measures signals
- AI validates results
- AI iterates firmware

Therefore instruments must be designed for **AI interaction**, not human interaction.

---

# 2. Core Philosophy

Traditional laboratory instruments are designed for humans and usually include:

- LCD screens
- Buttons and knobs
- Manual configuration
- Complex menu systems

AEL instruments are designed for **AI-first operation**.

AI does not need:

- screens
- knobs
- manuals

AI requires:

- APIs
- machine-readable data
- automatic discovery
- structured capability descriptions

Therefore AEL instruments are typically **headless devices controlled through APIs**.

---

# 3. Instrument Transport Architecture

AEL does not restrict hardware design.  
It defines **protocols and capability interfaces** instead.

Supported transports include:

- WiFi
- USB
- Ethernet
- PCIe

Each transport has different advantages.

---

# 4. WiFi Instruments

WiFi instruments are the easiest to deploy.

Typical hardware:

- ESP32
- WiFi-enabled MCUs

Examples:

- ESP32JTAG
- ESP32Meter
- UART probes
- GPIO signal probes

Advantages:

- wireless
- easy discovery
- low-cost hardware

Typical uses:

- GPIO monitoring
- UART capture
- power measurement
- simple logic analysis

---

# 5. USB Instruments

USB instruments provide:

- higher bandwidth
- lower latency
- stable connections

Possible devices:

- USB logic analyzers
- USB protocol analyzers
- USB power meters

Future designs may include:

USB3 high-speed analyzers capable of continuous data streaming.

---

# 6. Ethernet Instruments

Ethernet-connected instruments are suitable for lab environments.

Advantages:

- reliable connection
- high bandwidth
- long cable distance

Many professional instruments already support Ethernet control.

These can be integrated through adapters.

---

# 7. PCIe Instruments

PCIe instruments provide extremely high bandwidth.

Possible examples:

- FPGA capture cards
- RF acquisition systems
- ultra-high-speed logic analyzers

Advantages:

- direct memory access
- GB/s-level throughput
- real-time capture

---

# 8. Instrument Discovery

AEL instruments should support automatic discovery.

Example mechanisms:

WiFi:
- mDNS
- network scanning

USB:
- device VID/PID

Ethernet:
- network scanning
- registry services

PCIe:
- device enumeration

This allows AI agents to automatically detect available instruments.

---

# 9. Self-Describing Instruments

Each instrument should provide a description endpoint.

Example:

GET /instrument

Example response:

{
  "instrument_id": "esp32_meter_01",
  "type": "logic_probe",
  "vendor": "AEL",
  "version": "1.0",
  "capabilities": [
    "gpio_capture",
    "uart_monitor"
  ],
  "transport": "wifi"
}

This allows AI to understand:

- available capabilities
- supported operations
- communication method

---

# 10. Capability Model

Instrument functionality is defined through capabilities.

Examples:

- gpio_capture
- gpio_drive
- uart_monitor
- spi_sniffer
- power_measure
- jtag_control

AI agents use these capabilities to perform experiments.

---

# 11. Legacy Instrument Support

Traditional instruments may still be used if they support remote control.

Common interfaces:

- USB
- LAN
- SCPI

Integration requires an **adapter layer**.

Architecture:

AI Agent  
↓  
AEL Core  
↓  
Adapter Layer  
↓  
Legacy Instrument

Adapters translate AEL commands into device-specific commands.

---

# 12. User-Developed Instruments

AEL encourages users to build their own instruments.

Low-cost boards can be used:

- ESP32
- RP2040
- STM32

Requirements:

- implement AEL API
- provide capability description
- support communication transport

Examples:

- UART probe
- power monitor
- GPIO analyzer
- signal generator

Users can build instruments for as little as $10–$20.

---

# 13. Ecosystem Vision

Future AEL laboratories may include many distributed probes:

- AI Logic Analyzer
- AI UART Probe
- AI Power Probe
- AI SPI Sniffer
- AI RF Probe
- AI USB Analyzer

All instruments operate together in a network controlled by AI.

---

# 14. Platform Strategy

AEL defines:

- instrument protocol
- capability model
- discovery mechanism

It does **not require specific hardware designs**.

This enables:

- vendor instruments
- community instruments
- research instruments

---

# 15. Summary

AEL instruments follow three principles:

1. AI-first design
2. protocol-based interoperability
3. open ecosystem

Humans connect hardware.  
AI discovers instruments, runs experiments, and analyzes results.

This enables **autonomous AI-driven hardware laboratories**.
