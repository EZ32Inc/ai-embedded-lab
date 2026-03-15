# AEL — AI-Driven Embedded Lab

What if embedded development could feel like **vibe coding**?

Instead of manually writing firmware, reading datasheets, wiring instruments, and debugging step by step, you can describe what you want in natural language — and the system helps design experiments, generate firmware, run tests on real hardware, and analyze the results.

AEL is an experimental system that brings **vibe coding to embedded systems**.

It connects AI reasoning with a real embedded hardware lab. The system can generate firmware, design experiments, flash MCUs, capture signals, and verify behavior automatically.

Instead of stopping at code generation, AEL allows AI and the engineer to collaborate: designing tests, debugging failures, and completing experiments using evidence from real hardware.

This project explores a future where AI becomes an active engineering partner in embedded development.

---

## What AEL can do

AEL can automatically:

✔️ Generate firmware
✔️ Install toolchains (if missing)
✔️ Build projects
✔️ Flash target MCUs
✔️ Monitor UART logs
✔️ Detect crashes (panic / watchdog / reboot loops)
✔️ Capture and verify GPIO signals

All as part of a single automated pipeline.

---

## Why AEL?

Embedded development still relies heavily on manual iteration:

build → flash → observe → debug → repeat

AEL closes this loop using:

- AI-assisted project generation
- automated build & flash
- runtime monitoring
- hardware signal verification

And it works on **real hardware**, not simulations.

---

## How it works (Simplified)

```
Human → Orchestrator → Instrument → DUT (Target MCU)
```

Where:

- **Orchestrator** orchestrates the workflow and makes decisions
- **Instrument** provides debug access and signal capture
- **DUT** runs real firmware and produces observable behavior

---

## Example

Imagine:

- You have an STM32 board
- Its SWD is connected to an Instrument that supports Cortex MCU flash
- Its GPIOs P4–P7 are connected to capture inputs

You tell AEL:

> Generate firmware that outputs four different frequencies on P4–P7,
> build it, flash it, run it,
> and verify the signals are present.

AEL will:

1. Generate firmware
2. Build it
3. Flash the target
4. Run it
5. Capture signal behavior
6. Validate the result
7. Report PASS / FAIL

No manual intervention required.

---

## Reference Instrument: [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag)

AEL works with programmable **Instruments** that provide:

- debug access
- signal capture
- runtime monitoring

Today, **ESP32JTAG** serves as the first fully-supported Instrument.

It enables AEL to:

- flash firmware
- capture GPIO signals
- monitor UART output
- verify real hardware behavior

AEL itself is not tied to any specific hardware. [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) is simply the first concrete implementation of the AEL Instrument concept.

---

## Try AEL with Two Dev Boards (No Dedicated Hardware Required)

You don't need [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) to experience AEL.

A minimal setup uses:

- One ESP32-S3 dev board (Instrument)
- One RP2040 or STM32 or ESP32 dev board (DUT)

Total cost: under $20–$30.

The first board is a WiFi-based signal instrument that captures signals from the DUT or generates stimulus signals, and communicates with the Orchestrator over WiFi.

This allows AEL to build firmware, flash the target, run code, and verify signal behavior — without specialized hardware.

### Example Setup

Connect:

- ESP32 GPIO A → RP2040 IN0
- ESP32 GPIO B → RP2040 IN1
- ESP32 GPIO C → RP2040 IN2
- ESP32 GPIO D → RP2040 IN3
- GND → GND

Then tell AEL:

> Generate firmware with four different output frequencies,
> build it, flash it, run it, and verify signals.

AEL will compile, flash, run, measure, and validate automatically.

### Capability Comparison

| Setup | Auto Build | Flash | UART Monitor | Signal Verify |
|---|---|---|---|---|
| ESP32 only | ✔️ | ✔️ | ✔️ | ❌ |
| + RP2040 / STM32 | ✔️ | ✔️ | ✔️ | ✔️ |
| ESP32JTAG | ✔️ | ✔️ | ✔️ | ✔️ (higher speed & stability) |

---

## Some Use Case Examples

Here is an example using [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) as Instrument with an RP2040 Pico board:

![image](docs/images/20260302_esp32jtag_rp2040.jpg)

Another example uses two ESP32-S3 boards — one as Instrument to check GPIO levels, toggling, and target voltage; the other as DUT:

![image](docs/images/20260302_two_esp32s3.jpg)

A screenshot showing AEL and Codex running together on Ubuntu:

![image](docs/images/Screenshot_AEL_Codex_0302.png)

---

## Supported Targets (v0.1)

- RP2040
- STM32F103
- STM32F411
- ESP32-S3

And much more to come.

---

## Verified Boards

Boards that have completed full bring-up and sequential verification on real hardware.

| Board | MCU | Family | Experiments | Status | Doc |
|-------|-----|--------|-------------|--------|-----|
| STM32F411CEU6 (Black Pill) | STM32F411 | STM32F4 | 8 | verified | [docs/boards/stm32f411ceu6.md](docs/boards/stm32f411ceu6.md) |
| STM32F401RCT6 | STM32F401 | STM32F4 | 8 | verified | [docs/boards/stm32f401rct6.md](docs/boards/stm32f401rct6.md) |
| RP2040 Pico | RP2040 | RP2 | — | verified | — |
| ESP32-C6 DevKit | ESP32-C6 | ESP32 | — | verified | — |

---

## Terminology

An AEL lab consists of four core roles: Orchestrator, DUT, Instrument, Connections.

### Orchestrator

The system running AEL software. Typically a PC or server.

Responsible for:
- orchestration and decision making
- build & flash control
- verification logic

### DUT (Device Under Test)

The target system being developed or verified.

Examples:
- STM32 board
- RP2040 Pico
- ESP32-S3 target

Runs firmware and produces behavior.

### Instrument

A device that interacts with the DUT.

Instruments provide capabilities such as:

- debug access (SWD / JTAG)
- signal capture and generation
- UART monitoring
- measurement

Examples:
- [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag)
- RP2040 USB GPIO meter
- ESP32-S3 dev board (DIY instrument)
- External lab equipment

### Connections

Defines how DUTs are wired to Instruments.

Examples:

- SWD → Instrument Port P3
- DUT GPIO P4 → Capture IN0

Connections make automation reproducible.

### Together:

```
Orchestrator → Instruments → Connections → DUTs
```

---

## For AI Agents

See `docs/AI_USAGE_RULES.md` for CLI design rules and deterministic execution guidance.

---

## Latest Runs Helper

Use the helper script to quickly view the newest run folders and key logs:

```bash
tools/show_latest_runs.sh
tools/show_latest_runs.sh 3
```

It prints:

- latest run directories
- run status (`ok` / `fail`)
- key log paths (`preflight.log`, `build.log`, `flash.log`, `verify.log`)

---

## Workspace Cleanup

Use cleanup scripts to remove generated runs, artifacts, queue entries, reports, and cache files.

```bash
# Remove everything generated by AEL in this repo
tools/cleanup_workspce --full

# Preview what would be removed
tools/cleanup_workspce --full --dry-run

# Remove only entries older than a cutoff date/time
tools/cleanup_workspce 2026-03-06_15-10-59
tools/cleanup_workspce 2026-03-06
```

Notes:

- `tools/cleanup_workspce` is the compatibility alias (kept for existing usage).
- `tools/cleanup_workspace` is the canonical wrapper.
- `.gitkeep` placeholder files are preserved.

---

## Status

Early stage but actively used in daily development.

Feedback and contributions are welcome.

---

## Milestones

**v0.11-ai-loop** — AI-controlled hardware validation loop (2026-03-03)

AEL completed a full AI-driven hardware development loop using Codex:

- Generated a RunPlan
- Executed BUILD → LOAD → CHECK pipeline
- Flashed firmware to real hardware
- Captured UART logs and measured GPIO voltage
- Verified digital signature
- Detected a runtime failure, implemented a fix, re-ran the pipeline
- Achieved PASS on real hardware

**v0.11-autonomous-loop** — Autonomous development loop (2026-03-04)

AEL completed a full autonomous repository development cycle:

- Executed task queue sequentially
- Implemented minimal scoped changes
- Ran validation after every task
- Recorded task status with commit traceability
- Committed each completed step

Primary outputs: AIP HTTP instrument adapter, instrument manifest loader, AIP capability mapping, evidence writer helper, instrument contract validator.

---

## License

AEL is released under the [Apache 2.0 License](https://choosealicense.com/licenses/apache-2.0/).

You are free to:

- use it in personal projects
- integrate it into commercial products
- extend it for internal tooling

Third-party components and vendor code remain under their respective original licenses.
