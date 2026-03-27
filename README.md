# AEL — AI-Driven Embedded Engineering

AEL (AI Embedded Lab) is a new way of doing embedded engineering.

Instead of writing code, flashing firmware, and debugging manually,
you define the goal — and AI executes the workflow.

- AI generates firmware
- AI runs it on hardware or simulation
- AI analyzes results and fixes issues
- AI iterates until it works

This turns embedded development into a closed-loop system:

AI → Generate → Execute → Observe → Iterate

## 🚀 What is AEL?

- AI executes the embedded workflow end-to-end
- Humans define goals, not steps
- Development becomes a closed-loop system on real hardware

👉 Learn more: [AEL Paradigm Shift](docs/ael_paradigm_shift.md)

---

## 🚀 Installation and Getting Started

AEL is intentionally simple to install and easy to use.

1. Clone and set up the AEL repository.
2. Start an AI coding agent inside the repository, such as Codex or Claude Code.
3. Describe your goal in natural language.

That is the basic workflow.

You do not need to learn a large command surface before getting started. In the common case, you work inside the AEL repository with your AI agent and simply say what you want to do: bring up a board, generate firmware, run a test, investigate a failure, or validate a hardware feature. AEL provides the structure, assets, and command surface underneath, while the AI agent uses them to carry out the work.

This is one of AEL’s main advantages: it is powerful, but still easy to use. The experience is not centered on memorizing commands or manually stitching together tools. Instead, you install the repository, open an AI agent in that environment, and start working through natural language.

---

## Hardware

AEL is built for real hardware — but the barrier to entry is surprisingly low.

You can start with almost nothing:

- **ST-Link + an STM32 MCU/board** — a standard path, often just **$10–20 USD**
- **a single ESP32 dev board** — already enough to begin exploring AI-driven workflows
- **[ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) + a target board** — a next-gen, all-in-one instrument

---

### From "debug probe" → to "AI instrument"

Traditional tools like ST-Link do one thing well:
→ flash and debug

AI instrument like [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) changes the model:

- **Wireless (WiFi)** — no cables, AI can access it over the network
- **Flash firmware**
- **Capture signals at high speed (~256 MHz in supported setups)**
- **Generate stimulus signals**
- **Interact with hardware in real time**

Instead of multiple lab tools, you get **one programmable, networked instrument**.

---

### Why this matters

This is not just cheaper hardware.

It changes how embedded systems are developed:

- The instrument becomes **AI-controllable**
- The workflow becomes **fully automated**
- Hardware is no longer "manual-only"

In many cases, a **single ESP32 device can replace an entire entry-level lab setup**.

---

You do not need expensive equipment to begin.

AEL is designed so that **real hardware + AI** becomes accessible, programmable, and scalable.

---

## 🤖 Natural-Language-First Usage

AEL is designed to be driven by AI. Instead of relying on manual command-by-command operation, you describe your goal to the AEL Agent, for example through Codex or Claude Code running inside the repository.

### Example 1: New Hardware Bring-up
**User:** “I have an STM32F411 Black Pill and an ST-Link. Can you help me run a smoke test?”  
**AEL Agent:** “I can use ST-Link as the flashing and debug interface for your F411. I’ll generate a minimal smoke test, flash it, and verify startup through a mailbox signal. Shall I proceed?”

### Example 2: Feature Validation
**User:** “Generate firmware for my RP2040 that toggles GPIO 16 at 1 kHz, then verify the frequency.”  
**AEL Agent:** “I will generate the RP2040 firmware, build it, flash it to your Pico, and then use the connected Instrument to capture and verify the 1 kHz signal on GPIO 16. I’ll report the measured frequency back to you.”

### Example 3: Debugging
**User:** “My UART loopback test is failing on the G431. Can you investigate?”  
**AEL Agent:** “I’ll check the UART configuration in the firmware, verify the physical loopback connections using the Connection Doctor, and then rerun the test with additional debug logging enabled.”

Instead of stopping at code generation, AEL allows AI and the engineer to collaborate: designing tests, debugging failures, and completing experiments using evidence from real hardware.

This project explores a future where AI becomes an active engineering partner in embedded development.

---

## 🚀 Latest Milestone

### ESP32 Family Golden Suite Coverage — Major ESP32 Series Validated (2026-03-26)

AEL now has systematic golden test suite coverage across the major ESP32 families:

| Board | Family | Suite |
|-------|--------|-------|
| ESP32-WROOM-32D | ESP32 (original) | Rule-B |
| ESP32-C3 DevKit | ESP32-C3 | Rule-B |
| ESP32-C5 DevKit | ESP32-C5 | Rule-B |
| ESP32-C6 DevKit | ESP32-C6 | Rule-B |
| ESP32-S3 DevKit | ESP32-S3 | Rule-B |

Each board was validated against a consistently structured golden test suite covering the core peripheral set: GPIO, UART, SPI, ADC, PWM, interrupt handling, and board-specific features (WiFi, BLE, sleep modes, temperature sensor, NVS). The suite structure is uniform across families, making coverage directly comparable and results reproducible.

**What this represents for AEL:**

This is not ad-hoc board support added incrementally. Each entry was validated through the same systematic Rule-B methodology, with a firmware asset, a test pack, a golden record, and a detailed closeout report. The result is a coherent cross-family baseline that can serve as a regression anchor as the platform evolves.

**Closeout reports:**

- [`docs/reports/esp32_wroom32d_rule_b_closeout_2026-03-25.md`](docs/reports/esp32_wroom32d_rule_b_closeout_2026-03-25.md)
- [`docs/reports/esp32c3_devkit_rule_b_closeout_2026-03-26.md`](docs/reports/esp32c3_devkit_rule_b_closeout_2026-03-26.md)
- [`docs/reports/esp32c5_devkit_rule_b_closeout_2026-03-26.md`](docs/reports/esp32c5_devkit_rule_b_closeout_2026-03-26.md)
- [`docs/reports/esp32c6_devkit_rule_b_closeout_2026-03-25.md`](docs/reports/esp32c6_devkit_rule_b_closeout_2026-03-25.md)
- [`docs/reports/esp32s3_devkit_rule_b_closeout_2026-03-26.md`](docs/reports/esp32s3_devkit_rule_b_closeout_2026-03-26.md)

---

### Brownfield Embedded Project — AEL Drives a Real Firmware Project to Open-Source Release (2026-03-27)

AEL was applied to [`esp32jtag_firmware`](https://github.com/EZ32Inc/esp32jtag_firmware), an existing embedded firmware project for the ESP32JTAG instrument, as a concrete real-world test of AEL's engineering capabilities beyond greenfield prototyping.

This was not a demo or a toy project. The firmware had real hardware dependencies, an existing architecture, and outstanding work: bugs to fix, features to complete, issues to resolve, and a release to prepare. AEL was used to take over and drive that remaining work.

**What AEL did:**

- Reviewed the existing codebase and understood its architecture without starting from scratch
- Identified and fixed bugs across the firmware stack
- Resolved hardware bring-up issues encountered during integration testing
- Completed remaining features required for the release milestone
- Ran the project through validation against real hardware (RP2040 Pico DUT via SWD)
- Prepared the project for open-source publication

**The result:**

The firmware project was brought to release state and published as an open-source project. AEL contributed materially to the speed and quality of that outcome.

**Why this matters for AEL:**

Most AI-assisted embedded development work targets fresh greenfield projects. This milestone demonstrates that AEL can be applied to existing brownfield work — reviewing unfamiliar code, working within established constraints, and producing verifiable engineering outcomes on real hardware. That is a meaningfully harder problem, and a more representative test of practical utility.

📄 [ESP32JTAG Firmware Brownfield Onboarding Pattern](ael/civilization/) — experience captured in the Civilization Engine (`92fd939d`)

---

### RP2040 Pico + S3JTAG — Full Rule-B Golden Suite Validated (2026-03-26 / 2026-03-27)

AEL completed a full Rule-B golden test suite for the **RP2040 Pico** using the **S3JTAG** wireless instrument over WiFi. This is the first validated ARM Cortex-M + wireless instrument combination in AEL: SWD access, flash, and signal verification all happen over the network — no USB cable from the host to the debug probe.

**Instrument setup:**

- S3JTAG (ESP32-S3 based) acts as a networked BMDA (Black Magic Debug App) SWD probe
- Connected to RP2040 Pico via SWDIO, SWCLK, and signal wires
- All AEL pipeline operations (flash, GDB mailbox read, UART observe, signal capture) go through WiFi

**Test suite — 13 tests across three stages:**

| Stage | Test | Coverage |
|-------|------|----------|
| Stage 0 | `minimal_runtime_mailbox` | Basic bring-up gate — firmware boots and mailbox responds |
| Stage 1 | `internal_temp_mailbox` | Internal temperature sensor via ADC |
| Stage 1 | `timer_mailbox` | Hardware repeating timer ISR |
| Stage 2 | `gpio_level_low / high` | GPIO output levels via S3JTAG TARGETIN capture |
| Stage 2 | `gpio_signature_100hz / 1kHz` | GPIO frequency output measured by S3JTAG |
| Stage 2 | `pwm_capture` | PWM duty cycle and frequency capture |
| Stage 2 | `gpio_interrupt_loopback` | GPIO interrupt driven by loopback wire |
| Stage 2 | `uart_rxd_detect` | UART RX line detection via S3JTAG |
| Stage 2 | `uart_banner` | Full UART text output via S3JTAG Web UART bridge |
| Stage 2 | `spi_loopback` | SPI MOSI→MISO loopback |
| Stage 2 | `adc_loopback` | ADC input driven by GPIO output |

**Additional validated asset (2026-03-27):**

`timer_led_blink_ctrl` — a bidirectional mailbox test: firmware drives GPIO25 LED via a 10 ms timer ISR; AEL reads `led_state`, `toggle_count`, and `period_ms` from the mailbox via GDB, and can write `cmd_period_ms` to change the blink rate at runtime. Demonstrates live firmware observability over SWD.

**Rule-D combined firmware:**

A `full_suite` firmware asset runs all 13 sub-tests sequentially and reports results via UART through the S3JTAG Web UART bridge — a single flash covers the full board validation pass.

**Closeout reports:**

- [`docs/rp2040_s3jtag_full_suite_closeout_2026-03-26.md`](docs/rp2040_s3jtag_full_suite_closeout_2026-03-26.md) — pack-level full suite result
- [`docs/rp2040_s3jtag_standard_suite_closeout_2026-03-26.md`](docs/rp2040_s3jtag_standard_suite_closeout_2026-03-26.md)
- [`docs/rp2040_s3jtag_gpio_validation_closeout_2026-03-26.md`](docs/rp2040_s3jtag_gpio_validation_closeout_2026-03-26.md)
- [`docs/rp2040_s3jtag_pwm_validation_closeout_2026-03-26.md`](docs/rp2040_s3jtag_pwm_validation_closeout_2026-03-26.md)
- [`docs/rp2040_s3jtag_spi_validation_closeout_2026-03-26.md`](docs/rp2040_s3jtag_spi_validation_closeout_2026-03-26.md)
- [`docs/rp2040_s3jtag_uart_validation_closeout_2026-03-26.md`](docs/rp2040_s3jtag_uart_validation_closeout_2026-03-26.md)
- [`docs/rp2040_s3jtag_timer_led_blink_ctrl_closeout_2026-03-27.md`](docs/rp2040_s3jtag_timer_led_blink_ctrl_closeout_2026-03-27.md)

---

### AEL Experience System v0.1 — Record, Reuse, and Grow from Engineering Experience (2026-03-22)

AEL now records, reuses, and grows from engineering experience.

Completed in this milestone:

- **Experience Engine** — structured Experience Unit storage with confidence, tags, outcome, and feedback loop
- **Civilization Engine** (`ael/civilization/`) — the only layer that talks to the Experience Engine; pipeline never imports it directly
- **Closed Experience Loop** (`run → record → reuse`) — skills from past debugging sessions surface before the next run on the same board

The before-run protocol now outputs four sections every time a run begins:

1. Run statistics — N runs, S success / F failed, confidence
2. Known skills — fix/decision experiences relevant to this board and domain
3. Likely pitfalls — paths previously marked as dangerous
4. Observation focus — derived watch points from past failures

A new `record_skill()` entry point allows capturing reusable engineering fixes at the moment of realization — during or after a run, with no dependency on run-outcome sequence. Fields: `trigger`, `fix`, `lesson`, `scope`, `source_ref`.

AEL has moved from pure automation toward an experience-driven engineering system.

📄 [Full memo](docs/ael_experience_system_v0_1_memo_2026-03-22.md)
📄 [Civilization Engine v0.1 Spec](docs/AEL_Civilization_Engine_V0_1_Spec.md)
📄 [Civilization Engine essentials](docs/memo_AEL_Civilization_essentials.md)

---

### Schema Convergence Milestone — Default Verification Reached Parallel Stable Closure (2026-03-20)

The post-refactor validation result now shows that AEL has moved past "functionally working" and into a stable converged phase.

A six-platform, cross-instrument `default verification` baseline was run in full parallel mode for three consecutive rounds, and all three rounds passed without flaky behavior.

This milestone supports four concrete conclusions:

- system behavior has converged
- the schema abstraction and execution model are self-consistent
- the architecture is not showing hidden coupling or unstable resource contention on this baseline
- AI can now drive the full repo-native engineering loop repeatedly on real hardware with stable outcomes

What this means in practice:

- `default verification` is no longer only a feature demo or a one-off green run
- the repaired `ST-Link` path now holds inside the same parallel batch as the ESP32JTAG and meter-backed paths
- the recent schema and execution-layer changes now have repeated live-bench evidence behind them

Representative live evidence:

- first full six-way parallel pass: `2026-03-20_10-33-07`
- repeated six-way parallel passes:
  - `2026-03-20_10-36-49`
  - `2026-03-20_10-37-43`
  - `2026-03-20_10-38-37`
- all six experiments passed in each run set, including `stm32f103_gpio_no_external_capture_stlink`

This is the point where AEL starts to look less like "AI-assisted execution" and more like an `AI-reliable engineering system`.

📄 [Parallel stability closeout](docs/default_verification_parallel_stability_closeout_2026-03-20.md)
📄 [ST-Link recovery skill](docs/skills/stlink_parallel_default_verification_recovery_skill_2026-03-20.md)

### ESP32JTAG Native API Milestone — Minimal Instrument Interface Live-Validated (2026-03-19)

`ESP32JTAG` now has a minimal instrument-level native API on top of the
existing backend package.

This layer now explicitly owns:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `preflight_probe`

Its runtime model now explicitly presents `ESP32JTAG` as a multi-capability
instrument family with subsystem-oriented health domains:

- `network`
- `gdb_remote`
- `web_api`
- `capture_subsystem`
- `monitor_targets`

It is integrated through:

- `instrument_view`
- `instrument_doctor`
- `native_api_dispatch`

Healthy live sample already captured:

- `esp32jtag_stm32f411 @ 192.168.2.103`
- `ael instruments doctor --id esp32jtag_stm32f411`
- result: `ok = true`

Second healthy live sample:

- `esp32jtag_g431_bench @ 192.168.2.62`
- `ael instruments doctor --id esp32jtag_g431_bench`
- result: `ok = true`

Additional healthy live samples:

- `esp32jtag_rp2040_lab @ 192.168.2.63`
- `esp32jtag_h750_bench @ 192.168.2.106`
- both returned `ok = true`

This means `ESP32JTAG` is now legible both as:

- a unified action backend
- a named multi-capability instrument interface

📄 [ESP32JTAG native API closeout](docs/esp32jtag_native_api_closeout_2026-03-19.md)

### ESP32 Instrument Backend Milestone — Meter Runtime Path Revalidated (2026-03-19)

After the backend unification work:

- `esp32_meter` action execution is now unified behind the backend package
- `usb_uart_bridge` is package-aligned with the same backend family
- `esp_remote_jtag` is now bounded as a legacy shim instead of a live mixed implementation

This was also revalidated on a real meter-backed runtime path:

- `esp32c6_gpio_signature_with_meter`
- instrument: `esp32s3_dev_c_meter @ 192.168.4.1:9000`
- result: `PASS`
- run id: `2026-03-19_10-34-45_esp32c6_devkit_esp32c6_gpio_signature_with_meter`

The practical result is that the runtime consumer path still works on real hardware after the meter action path moved behind the unified backend boundary.

### Instrument Backend Milestone — ESP32 Meter Consumer Migration and Legacy Backend Cleanup (2026-03-19)

AEL's instrument backend layout is now substantially cleaner and more uniform.

- `esp32_meter` now has unified backend packaging and real consumer-path usage
- `usb_uart_bridge` is now package-aligned with the rest of the backend family
- `esp_remote_jtag` is no longer treated as an active mixed backend; it is now a
  legacy compatibility shim over:
  - `esp32_jtag`
  - `esp32_meter`

This means the main instrument backend family is now much clearer:

- `stlink_backend`
- `esp32_jtag`
- `esp32_meter`
- `usb_uart_bridge`

And the old overlapping path is now explicitly bounded as legacy:

- `esp_remote_jtag`

### STM32 Cross-Instrument Milestone — Shared Test Packs Across ST-Link and [ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag) (2026-03-19)

AEL now has validated dual-instrument support for shared test-pack execution on both:

- `STM32F103C8T6 Bluepill GPIO Bench`
- `STM32F407 Discovery`

The same validation methodology now works across two instrument paths:

- `ST-Link`
- `ESP32JTAG`

This milestone proves that, for the same DUT family and shared test assets, AEL can switch instrument paths without changing the test intent.

**STM32F103C8T6 pack family:**

- shared base pack:
  - `packs/smoke_stm32f103_gpio_loopbacks_base.json`
- instrument-specific child packs:
  - `packs/smoke_stm32f103_gpio_loopbacks_stlink.json`
  - `packs/smoke_stm32f103_gpio_loopbacks_esp32jtag.json`

**STM32F103C8T6 shared tests validated:**

- `stm32f103_gpio_no_external_capture`
- `stm32f103_uart_loopback_mailbox`
- `stm32f103_spi_mailbox`
- `stm32f103_exti_mailbox`
- `stm32f103_adc_mailbox`

**STM32F103C8T6 results:**

- `ESP32JTAG + STM32F103C8T6`: `5/5 PASS`
- `ST-Link + STM32F103C8T6`: `5/5 PASS`

**STM32F407 mailbox pack family:**

- shared base pack:
  - `packs/smoke_stm32f407_mailbox_base.json`
- instrument-specific child packs:
  - `packs/smoke_stm32f407_mailbox_stlink.json`
  - `packs/smoke_stm32f407_mailbox_esp32jtag.json`

**STM32F407 shared test validated:**

- `stm32f407_mailbox`

**STM32F407 results:**

- `ESP32JTAG + STM32F407`: repeated live passes
- `ST-Link + STM32F407`: repeated live passes

**What this proves:**

- shared pack / child-pack structure works on real hardware
- the same DUT-side validation assets can run through two instrument paths
- instrument-specific execution details can stay in board/child-pack configuration
- cross-instrument debug can expose tool-path issues without invalidating shared firmware/test methodology

**Key debug conclusion from this milestone sequence:**

- `ST-Link` mailbox verify failures on this path were not caused by DUT wiring or loopback logic
- the real issue was `st-util` session semantics in `check_mailbox_verify`
- for `skip_attach` sessions, `disconnect` is correct and `detach` is not

📄 [STM32F103 closeout](docs/stm32f103_gpio_cross_instrument_closeout_2026-03-19.md)
📄 [STM32F103 ST-Link child pack](packs/smoke_stm32f103_gpio_loopbacks_stlink.json)
📄 [STM32F103 ESP32JTAG child pack](packs/smoke_stm32f103_gpio_loopbacks_esp32jtag.json)
📄 [STM32F407 closeout](docs/stm32f407_shared_mailbox_stability_closeout_2026-03-18.md)
📄 [STM32F407 ST-Link child pack](packs/smoke_stm32f407_mailbox_stlink.json)
📄 [STM32F407 ESP32JTAG child pack](packs/smoke_stm32f407_mailbox_esp32jtag.json)

---

### STM32F407 Discovery — ST-Link + STM32 board support added (7/7 PASS, 2026-03-18)

AEL completed full bring-up and validation on STM32F407VGT6 Discovery using the onboard ST-Link V2 instrument path (USB → st-util GDB server → SWD).

**All 7 tests passed:**

- mailbox (basic run verification)
- timer interrupt (TIM3 at 100ms intervals, 10 interrupts for PASS)
- GPIO loopback (PB0 → PB1)
- UART loopback (USART2 PD5 → PD6, 115200 8N1)
- EXTI trigger (PB8 → PB9, 10 rising edges via SYSCFG routing)
- ADC loopback (PC0 → PC1, 12-bit, software-start)
- SPI loopback (PB15 MOSI → PB14 MISO, SPI2 master mode 0)

**Key notes:**

- Firmware generated by AI (bare-metal C, direct register access, no HAL). Zero human code written.
- Uses `monitor reset run` after `load` — st-util leaves target halted without it.
- USART2/PD5/PD6 used instead of USART1/PA9/PA10 — onboard ST-Link UART bridge occupies PA9/PA10.
- All 5 loopback jumpers placed once; no re-wiring between tests.

📄 [Full session record](docs/stm32f407_validation_session_record.md)
📄 [Smoke pack](packs/smoke_stm32f407.json)

---

### STM32H750 — Full Smoke Validation (7/7 PASS)

AEL successfully completed full bring-up and validation on STM32H750.

**All tests passed:**

- minimal_runtime_mailbox
- wiring_verify
- adc_dac_loopback
- gpio_loopback
- uart_loopback
- exti_trigger
- pwm_capture

### What this proves

- Autonomous firmware generation and execution
- Multi-domain validation (digital, analog, timing, interrupt, communication)
- Real hardware debugging and strategy adaptation
- Rule extraction from failures

👉 This marks the first full autonomous bring-up on STM32H7-class MCU.

### Key Insight

The primary bottleneck has shifted from software to physical wiring.

→ Next phase: reconfigurable socket + FPGA routing fabric

---

📄 [Full postmortem](docs/methodology/stm32h750_milestone_postmortem_v0_1.md)
📄 [Smoke pack](packs/smoke_stm32h750.json)

---

### STM32G431 — Full Smoke Validation (9/9 PASS)

AEL completed full bring-up and validation on STM32G431CBU6.

**All tests passed:**

- minimal_runtime_mailbox
- gpio_signature
- uart_loopback
- spi
- adc
- capture
- exti
- gpio_loopback
- pwm

**Key fixes during bring-up:**

- SPI: `CR2.FRXTH=1` required to lower RXNE threshold to 8-bit (G4 FIFO, not present on F4)
- ADC: `ADC12_CCR.CKMODE=01` required to select synchronous clock (async default needs PLL)

👉 First board to use the `minimal_runtime_mailbox` Step 0 debug-path gate as part of the pack.

📄 [Full postmortem](docs/methodology/stm32g431_milestone_postmortem_v0_1.md)
📄 [Smoke pack](packs/smoke_stm32g431.json)

---

### STM32F411 / STM32F401 — Verified (8/8 PASS)

AEL completed full bring-up on both STM32F4-family boards.

**STM32F411CEU6 (Black Pill)** and **STM32F401RCT6** — 8 experiments each:

- gpio_signature
- uart_loopback
- spi
- adc
- capture
- exti
- gpio_loopback
- pwm

These boards established the reference bring-up template used for all subsequent targets.

📄 [STM32F411 board doc](docs/boards/stm32f411ceu6.md)
📄 [STM32F401 board doc](docs/boards/stm32f401rct6.md)
📄 [F411 smoke pack](packs/smoke_stm32f411.json) | 📄 [F401 smoke pack](packs/smoke_stm32f401.json)

---

### STM32F407 Discovery — Smoke Pack Baseline (7/7 PASS, ST-Link)

AEL includes a fully validated STM32F407 Discovery smoke pack using ST-Link (st-util).

**Run:**

```bash
python3 -m ael pack --pack packs/smoke_stm32f407.json --board stm32f407_discovery
```

**Coverage — 7 tests:**

- mailbox (basic run verification)
- timer interrupt (TIM3)
- GPIO loopback (PB0 → PB1)
- UART loopback (USART2 PD5 → PD6)
- EXTI trigger (PB8 → PB9)
- ADC loopback (PC0 → PC1)
- SPI loopback (PB15 → PB14)

**Wiring:**

```
PB0  -> PB1
PD5  -> PD6
PB8  -> PB9
PC0  -> PC1
PB15 -> PB14
```

**Notes:**

- On STM32F4 Discovery, avoid PA9/PA10 for UART loopback — the onboard ST-Link UART bridge circuit causes interference. Use USART2 PD5/PD6 instead.
- When using st-util, GDB `load` does not start execution automatically. The board config includes `monitor reset run` to handle this.

This pack is fully validated (7/7 PASS) and serves as the regression baseline for STM32F407 + ST-Link in AEL.

📄 [Baseline document](docs/methodology/smoke_stm32f407_baseline_v0_1.md)
📄 [Smoke pack](packs/smoke_stm32f407.json)

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

Today, **[ESP32JTAG](https://www.crowdsupply.com/ez32/esp32jtag)** serves as the first fully-supported Instrument.

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

## Golden-Standard Validated MCUs

MCUs that have completed real-hardware validation at AEL's current golden-standard level.

- `STM32F103C8T6`
  - validated with shared cross-instrument loopback pack on both `ST-Link` and `ESP32JTAG`
- `STM32F103RCT6`
  - validated with full `7/7 PASS` smoke suite
- `STM32F401RCT6`
  - validated with full `8/8 PASS` smoke suite
- `STM32F411CEU6`
  - validated with full `8/8 PASS` smoke suite
- `STM32F407VGT6`
  - validated on `STM32F407 Discovery`
  - shared mailbox path validated on both `ST-Link` and `ESP32JTAG`
  - full `7/7 PASS` smoke baseline validated on `ST-Link`
- `STM32G431CBU6`
  - validated with full `9/9 PASS` smoke suite
- `STM32H750VBT6`
  - validated with full `7/7 PASS` smoke suite
- `RP2040`
  - validated in current AEL verified-board baseline
- `ESP32-C6`
  - validated in current AEL verified-board baseline

---

## Verified Boards

Boards that have completed full bring-up and sequential verification on real hardware.

| Board | MCU | Family | Experiments | Status | Doc |
|-------|-----|--------|-------------|--------|-----|
| STM32F103 GPIO Bench | STM32F103C8T6 | STM32F1 | 5 | verified (ST-Link + ESP32JTAG) | [docs/stm32f103_gpio_cross_instrument_closeout_2026-03-19.md](docs/stm32f103_gpio_cross_instrument_closeout_2026-03-19.md) |
| STM32F103RCT6 board | STM32F103RCT6 | STM32F1 | 7 | verified | [docs/boards/stm32f103rct6.md](docs/boards/stm32f103rct6.md) |
| STM32F407 Discovery | STM32F407VGT6 | STM32F4 | 7 | verified (ST-Link baseline + dual-instrument mailbox) | [docs/methodology/smoke_stm32f407_baseline_v0_1.md](docs/methodology/smoke_stm32f407_baseline_v0_1.md) |
| STM32F411CEU6 (Black Pill) | STM32F411 | STM32F4 | 8 | verified | [docs/boards/stm32f411ceu6.md](docs/boards/stm32f411ceu6.md) |
| STM32F401RCT6 | STM32F401 | STM32F4 | 8 | verified | [docs/boards/stm32f401rct6.md](docs/boards/stm32f401rct6.md) |
| STM32G431CBU6 | STM32G431CBU6 | STM32G4 | 9 | verified | [docs/methodology/stm32g431_milestone_postmortem_v0_1.md](docs/methodology/stm32g431_milestone_postmortem_v0_1.md) |
| STM32H750VBT6 YD | STM32H750VBT6 | STM32H7 | 7 | verified | [docs/methodology/stm32h750_milestone_postmortem_v0_1.md](docs/methodology/stm32h750_milestone_postmortem_v0_1.md) |
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

## License

AEL is released under the [Apache 2.0 License](https://choosealicense.com/licenses/apache-2.0/).

You are free to:

- use it in personal projects
- integrate it into commercial products
- extend it for internal tooling

Third-party components and vendor code remain under their respective original licenses.
