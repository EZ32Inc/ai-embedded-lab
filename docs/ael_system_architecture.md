# AEL System Architecture

This diagram shows how **AI, AEL, and the hardware lab interact**.

AEL acts as the **execution kernel** that allows AI to safely operate real embedded hardware.

---

# 1. System Overview

                +----------------------+
                |        AI Agent      |
                |  (Codex / GPT / etc)|
                +----------+-----------+
                           |
                           |
                Code / Plan / Analysis
                           |
                           v
                   +---------------+
                   |      AEL      |
                   |  CLI + Core   |
                   +-------+-------+
                           |
                           v
                     +-----------+
                     |  Runner   |
                     +-----------+
                           |
                    Execute RunPlan
                           |
                           v
                   +---------------+
                   | Adapter Layer |
                   +-------+-------+
                           |
    +----------------------+-----------------------+
    |                      |                       |
    v                      v                       v

Build Adapters Load Adapters Check Adapters
| | |
v v v
Build Systems Debug / Flash Tools Observers
Instruments


---

# 2. Hardware Interaction Layer

Adapters interact with real hardware through probes and instruments.

                 +----------------+
                 | Adapter Layer  |
                 +--------+-------+
                          |
   +----------------------+-------------------+
   |                      |                   |
   v                      v                   v

Debug Probes Instruments Observers
| | |
v v v
JTAG / SWD GPIO / ADC UART / Logic
| | |
+----------+-----------+-------------------+
|
v
Target Hardware


Examples:

Debug probes

- ESP32JTAG
- STLink
- WCH-Link
- Black Magic Probe

Instruments

- ESP32 meter board
- logic analyzer
- voltage measurement

Observers

- UART logs
- GPIO signal capture
- instrument measurements

---

# 3. AI-Controlled Development Loop

The most important capability of AEL is enabling an **AI-driven firmware development loop**.

      AI modifies firmware
                |
                v
          Generate RunPlan
                |
                v
             AEL Runner
                |
                v
    +---------------------------+
    |   BUILD → LOAD → CHECK    |
    +---------------------------+
                |
                v
          Hardware Results
                |
                v
          result.json
                |
                v
            AI Analysis
                |
                v
         Fix / Improve Code
                |
                v
           Repeat Loop

This loop allows AI to:

- build firmware

- automatic test generation
