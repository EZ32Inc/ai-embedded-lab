# AEL — AI Embedded Lab

AEL orchestrates Instruments interacting with DUTs (real hardware running firmware) to automatically build, run and verify their behavior.

---

**Tell AEL what you connected. Tell it what you want.  
It builds, flashes, runs, measures and reports — on real hardware.**

AEL turns embedded development into a **vibe coding experience**:

Instead of manually:

- building firmware  
- flashing targets  
- watching UART logs  
- probing GPIO signals  

You describe:

- your board  
- how it's connected  
- what you want to verify  

AEL handles the rest.

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

## For AI Agents

See `docs/AI_USAGE_RULES.md` for CLI design rules and deterministic execution guidance.

---

## Supported Targets (v0.1)

- RP2040  
- STM32F103  
- ESP32-S3  

---

## Example

Imagine:

- You have an STM32 board  
- Its SWD is connected to a debug node  
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

## Reference Lab Node: [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag)

AEL works with programmable **Instrument** that provide:

- debug access  
- signal capture  
- runtime monitoring  

Today, **ESP32JTAG** serves as the first fully-supported Instrument.

It enables AEL to:

- flash firmware  
- capture GPIO signals  
- monitor UART output  
- verify real hardware behavior  

AEL itself is not tied to any specific hardware.

[ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) is simply the first concrete implementation of this lab node concept.

Future nodes (including ezLink) will expand this capability.

---

## Try AEL with Two Dev Boards (No Dedicated Hardware Required)

You don’t need [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) to experience AEL.

A minimal setup uses:

- One ESP32-S3 dev board (target)
- One RP2040 or STM32 dev board (instrument)

Total cost: under $20–$30.

The second board acts as a simple USB-based signal instrument.

This allows AEL to:

- build firmware  
- flash target  
- run code  
- verify signal behavior  

without specialized hardware.

---

### Example Setup

Connect:

- ESP32 GPIO A → RP2040 IN0  
- ESP32 GPIO B → RP2040 IN1  
- ESP32 GPIO C → RP2040 IN2  
- ESP32 GPIO D → RP2040 IN3  
- GND → GND  

Then tell AEL:

> Generate firmware with four different output frequencies  
> build it, flash it, run it,  
> and verify signals.

AEL will:

- compile  
- flash  
- run  
- measure
- validate  

automatically.

---

### Capability Comparison

| Setup | Auto Build | Flash | UART Monitor | Signal Verify |
|---|---|---|---|---|
| ESP32 only | ✔️ | ✔️ | ✔️ | ❌ |
| + RP2040 / STM32 | ✔️ | ✔️ | ✔️ | ✔️ |
| ESP32JTAG | ✔️ | ✔️ | ✔️ | ✔️ (higher speed & stability) |

---

## How it works (Simplified)

Human → AEL → Lab Node → Target MCU

Where:

- AEL orchestrates the workflow  
- Lab Node provides debug & capture  
- Target runs real firmware  

---

## Some use case examples

Here is example how we use [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) as Instrument and RP2040 PICO board.
![image](docs/images/20260302_esp32jtag_rp2040.jpg)

Another example is using two ESP32S3 boards, one as Instrument to check GPIO levels and toggling and target voltage of the DUT, another ESP32S3 dev board is used as DUT or the target system being developed/verified.
![image](docs/images/20260302_two_esp32s3.jpg)

This is a screenshot showing how we use AEL and Codex in Ubuntu OS:
![image](docs/images/Screenshot_AEL_Codex_0302.png)

---

## Quick Reality Check

AEL aims to provide a web-coding-like experience for embedded development:

Describe your board → AEL executes the hardware loop.

Today, this intent is expressed via:

- board profiles  
- wiring configuration  
- test packs  

rather than full natural language interaction.

This keeps the system deterministic and reliable while still enabling full automation.

Natural-language workflows are a future direction.

---
## Terminology

An AEL lab consists of four core roles: Orchestrator, DUT, Instrument, Connections.

### Orchestrator
The system running AEL software.

Typically a PC or server.

Responsible for:
- orchestration
- decision making
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
- signal capture
- signal generation
- UART monitoring
- measurement

Examples:
- [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag)
- RP2040 USB GPIO meter
- Future ezLink
- External lab equipment

### Connections

Defines how DUTs are wired to Instruments.

Examples:

- SWD → Instrument Port P3
- DUT GPIO P4 → Capture IN0

Connections make automation reproducible.

### Together:

Orchestrator → Instruments → Connections → DUTs

---

## License

AEL is released under the MIT License.

The goal is to make it easy for developers, startups and hardware teams to experiment with AI-driven embedded workflows without legal friction.

You are free to:

- use it in personal projects  
- integrate it into commercial products  
- extend it for internal tooling  

See the [LICENSE](LICENSE) file for details.

---

## Status

Early stage but actively used in daily hardware development.

Feedback and contribution is welcome.
