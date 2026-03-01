# AEL Concept Model

This project uses the following conceptual roles:

Orchestrator:
Runs AEL orchestration logic.

DUT:
Device Under Test.
Target boards such as STM32, RP2040, ESP32.

Instrument:
Hardware capable of interacting with DUTs.
Examples: ESP32JTAG, RP2040 GPIO meter.

Connections:
Defines wiring between DUTs and Instruments.

---

These are conceptual roles.

They may map to:

- configs
- adapters
- bench definitions

Code structure does not need to mirror these names directly.
