# Current Validated Capabilities

This document summarizes the public `master` branch. It intentionally avoids
bench-local IP addresses and private setup details. For live truth, use:

```bash
python3 -m ael inventory list --format text
python3 -m ael verify-default state
```

---

## Validation Model

AEL tracks several confidence levels:

- **canonical golden**: validated path promoted to the main system baseline
- **golden / legacy golden**: validated path retained for compatibility or a
  specific fixture
- **candidate / draft**: useful path that is not yet a public baseline
- **report-only evidence**: historical closeout or investigation evidence

The CLI inventory is the preferred source for exact current labels.

---

## Public Golden Coverage

The public branch contains validated paths across these families:

| Family / board class | Representative status |
|---|---|
| WCH CH32V203 | Golden suite validated, `23/23 PASS` |
| WCH CH32V305 | Golden suite validated, `25/25 PASS` |
| WCH CH32V003 | Golden subset validated, currently `13/13` after removing an unsafe sleep test |
| nRF52840 nice!nano | Zephyr/UF2-oriented golden suite validated, `15/15 PASS` |
| STM32F103 / STM32F401 / STM32F411 / STM32F407 | Multiple golden or canonical-golden suites validated |
| STM32F030 / STM32G431 / STM32H563 / STM32U585 / STM32H750 | Validated reports and/or golden-suite records present |
| RP2040 Pico | GPIO, UART, SPI, PWM, timer, temperature, and signal-validation paths present |
| ESP32 C3/C5/C6/S3/WROOM32D | Several native and dual-USB paths are represented in inventory; exact pack availability should be checked with the CLI |

Representative reports:

- [CH32V203 closeout](./reports/ch32v203_nanoch32v203_golden_suite_closeout_2026-04-12.md)
- [CH32V305 report](../reports/ch32v305xxx_golden_suite_report.md)
- [nRF52840 nice!nano closeout](./reports/nrf52840_nicenano_golden_suite_closeout_2026-04-12.md)
- [STM32F030 closeout](./reports/stm32f030c8t6_golden_suite_closeout_2026-04-03.md)
- [STM32F407 report](../reports/stm32f407vet6_golden_suite_report.md)

---

## Current Practical Strengths

- Staged execution: plan, pre-flight, run, check, report.
- Pack execution for board-level golden suites.
- Board/test/instrument inventory through the CLI.
- Mailbox-based bare-metal verification for many Cortex-M and RISC-V targets.
- UART observation and USB/UF2-oriented flows for selected boards.
- Evidence-oriented closeout reports for real hardware validation.
- Project domain separation: user projects live under `projects/`, while system
  capabilities live under configs, assets, packs, and test plans.

---

## Current Known Gaps

- Some docs and reports predate the current inventory and should be treated as
  historical unless confirmed by CLI output.
- Some ESP32 inventory entries reference pack names that are not present on the
  public branch; use `inventory list` before promising a runnable suite.
- The default verification manifest may be unavailable or stale on a machine
  that has not recently run default verification.
- Bench readiness is not implied by repository support. Users must confirm their
  board, instrument, wiring, power, and serial/debug access.
- Instrument abstraction is still evolving; older docs may use probe-first
  language where current docs prefer instrument/control-instrument wording.

---

## Recommended Current Workflow

1. Start from `python3 -m ael inventory list --format text`.
2. Confirm the target board and exact fixture.
3. Inspect the test or pack with `inventory describe-test` and
   `inventory describe-connection`.
4. Run one low-risk smoke test before running a full pack.
5. Record meaningful live validation with a closeout report and reusable skill
   capture when a new pack or capability is formalized.

---

## Maintenance Note

This file should be refreshed after each public golden-suite promotion or major
inventory change. Do not copy private bench IP addresses or local filesystem
paths into this document.
