# AEL Terminology Reference

Version: draft-0.1
Date: 2026-03-29
Status: Under Review

---

## Overview

AEL uses four core concepts to organize hardware validation work. Each concept has a distinct scope, a distinct file (or directory), and a distinct command that operates on it. Understanding their boundaries prevents confusion when naming files, writing prompts, or designing new test coverage.

```
Project
  └── Suite
        ├── Pack  (Stage 0)
        ├── Pack  (Stage 1)
        └── Pack  (Stage 2)
              ├── Test
              ├── Test
              └── Test
                    └── Firmware
```

---

## Test

**The atomic unit of validation.**

A Test describes a single, self-contained validation intent: which firmware to build, what signals or mailbox values to verify, and how to interpret the result.

| Property | Value |
|----------|-------|
| File location | `tests/plans/<board>/<name>.json` |
| Schema field | `test_kind`, `covers`, `build`, `mailbox_verify`, `signal_checks` |
| Covers | One peripheral or one behavior (GPIO, UART, EXTI, PWM capture, …) |
| Run by | `ael run --test <path>` |
| Produced by | Human or AI, one per firmware target |

**Examples:**
- `tests/plans/stm32f401rct6_exti_trigger.json` — tests EXTI6 via EXTI_PR polling
- `tests/plans/rp2040_uart_banner_with_s3jtag.json` — tests UART TX/RX banner round-trip
- `tests/plans/esp32c6_devkit/test_pcnt.json` — tests PCNT pulse count loopback

**Rule:** A Test file never specifies which board instance to use, which instrument to connect, or what physical wiring the bench has. Those are resolved at runtime by the Pack and Bench Profile.

---

## Pack

**The runnable unit.**

A Pack groups a set of Tests that share a board and a bench configuration, and can be executed in a single `ael pack` command. A Pack answers the question: *"Given this board on this bench, which tests should I run together?"*

| Property | Value |
|----------|-------|
| File location | `packs/<name>.json` |
| Schema fields | `name`, `board`, `bench_profile`, `tests[]`, `notes` |
| Covers | One stage of validation for one board variant |
| Run by | `ael pack --pack <path>` |
| Produced by | Human or AI, one per validation stage |

**Examples:**
- `packs/stm32f401rct6_stage0.json` — smoke tests, no wiring required
- `packs/stm32f401rct6_stage2.json` — wired loopback tests (PA8↔PA6, PA9↔PA10, PB0↔PB1)
- `packs/esp32c6_devkit_stage2.json` — GPIO_INTR, PCNT, UART, ADC, SPI, I2C with 6 jumpers

**Rule:** A Pack owns the bench_profile selection. Different Packs for the same board can reference different bench profiles (e.g., stage1 uses `default`, stage2 uses `stage3` wiring). All Tests within a Pack share the same bench configuration.

### Pack naming convention

```
<board_id>_stage<N>.json          # staged validation (preferred)
<board_id>_<topic>.json           # topic-focused subset (e.g., _uart_only)
<board_id>_full.json              # all tests flattened into one pack (legacy)
```

---

## Suite

**A named, ordered collection of Packs representing a complete validation journey.**

A Suite answers the question: *"What is the full sequence of steps to validate this board from zero to production-ready?"* Each step in a Suite is a Pack (typically a Stage). Suites make the stage dependency explicit: Stage N should only run if Stage N-1 passed.

| Property | Value |
|----------|-------|
| File location | `suites/<name>.json` *(proposed)* |
| Schema fields | `name`, `board`, `stages[]`, `gate` |
| Covers | The full bring-up arc for one board or board family |
| Run by | `ael suite --suite <path>` *(proposed)* |
| Produced by | Human, once per board when the stage structure is stable |

**Proposed schema:**
```json
{
  "name": "stm32f401rct6_golden",
  "description": "Complete STM32F401RCT6 bring-up validation",
  "board": "stm32f401rct6",
  "gate": "stop_on_stage_fail",
  "stages": [
    { "name": "stage0",        "pack": "packs/stm32f401rct6_stage0.json" },
    { "name": "stage0_mailbox","pack": "packs/stm32f401rct6_stage0_mailbox.json" },
    { "name": "stage1",        "pack": "packs/stm32f401rct6_stage1.json" },
    { "name": "stage2",        "pack": "packs/stm32f401rct6_stage2.json" }
  ]
}
```

**Existing real-world examples (before Suite was formalized):**
- `packs/rp2040_s3jtag_full.json` — this is semantically a Suite flattened into a single Pack. The pack's own `notes` field explicitly calls out "Stage 0, Stage 1, Stage 2 coverage." This is the problem Suites solve: a flat Pack loses stage ordering and gate semantics.
- `packs/esp32c6_devkit_stage0/1/2.json` — three separate Packs that together form the ESP32-C6 Suite, but there is no file that names and orders them.

**Gate options:**

| Value | Behavior |
|-------|----------|
| `stop_on_stage_fail` | Halt the suite at the first Pack that has any FAIL |
| `run_all` | Run all Packs regardless of failures, collect full report |

**Rule:** "Suite" should not be used in Pack file names. A file named `esp32c5_full_suite.json` is a Pack (it is in `packs/` and is run by `ael pack`), not a Suite. The word "suite" in that filename is informal. Prefer `_full` or `_all` for such aggregated Packs.

---

## Project

**A stateful, goal-oriented record that spans multiple runs over time.**

A Project answers the question: *"What is the user trying to accomplish, what has been confirmed, and what is still blocked?"* It is not directly runnable; it is a tracking artifact that ties together runs, evidence, and intent.

| Property | Value |
|----------|-------|
| File location | `projects/<id>/project.yaml` |
| Schema fields | `domain`, `confirmed_facts[]`, `current_blocker`, `last_action`, `cross_domain_links[]` |
| Covers | A user-defined goal (bring-up, integration, certification prep…) |
| Managed by | `ael project` subcommand |
| Produced by | AI or human at the start of a multi-session engagement |

**Examples:**
- `projects/stm32f401rct6_bringup/` — goal: run all banner experiments matching F411 suite
- `projects/stm32g431_bringup/` — goal: validate STM32G431 from scratch

**A Project links to Suites and Packs indirectly** via `run` links and `capability_ref`. A Project is the only concept that has memory across sessions. The others (Suite, Pack, Test) are stateless artifacts.

**Rule:** Do not store wiring, bench state, or "what I did today" in a Project. Those belong in run artifacts and CE (Civilization Engine) records. A Project holds confirmed, durable facts and current blockers only.

---

## Firmware

**The embedded binary that a Test exercises.**

Firmware is not a first-class AEL concept (there is no `firmware run` command), but it is the foundation everything else rests on. Each Test has exactly one Firmware. The Test's `build` block tells the pipeline how to compile and flash it.

| Property | Value |
|----------|-------|
| File location | `firmware/targets/<name>/` |
| Key files | `main.c`, `Makefile`, `<board>.ld`, `startup.c` |
| Built by | `ael` pipeline (make) during Pack execution |

---

## Bench Profile

**The physical wiring contract for a Pack.**

A Bench Profile is not a test concept — it describes the lab bench: which signals are connected to which instrument channels, and what the default SWD/reset/verify wiring is. One board can have multiple Bench Profiles for different wiring configurations (e.g., `__default` for basic bringup, `__stage3` for full loopback).

| Property | Value |
|----------|-------|
| File location | `configs/bench_profiles/<board_id>__<name>.yaml` |
| Selected by | Pack (`bench_profile` field) > Board (`default_bench_profile`) |
| Covers | `bench_connections`, `observe_map`, `verification_views`, `default_wiring`, `safe_pins` |

---

## Summary Table

| Concept | File | Runnable? | Stateful? | Scope |
|---------|------|-----------|-----------|-------|
| Test | `tests/plans/*.json` | via Pack | No | One peripheral/behavior |
| Pack | `packs/*.json` | Yes (`ael pack`) | No | One stage, one bench config |
| Suite | `suites/*.json` *(proposed)* | Proposed | No | Full validation arc (ordered Packs) |
| Project | `projects/*/project.yaml` | No | **Yes** | User goal across sessions |
| Firmware | `firmware/targets/*/` | No (built by Pack) | No | Embedded binary |
| Bench Profile | `configs/bench_profiles/*.yaml` | No | No | Physical wiring contract |

---

## Terminology Anti-Patterns

These usages cause confusion and should be avoided:

| Anti-pattern | Problem | Preferred usage |
|--------------|---------|-----------------|
| Calling a Pack a "Suite" | Loses stage ordering, gate semantics | Use "Pack" for `packs/*.json` files |
| `*_full_suite.json` in `packs/` | The word "suite" implies an ordered collection; this is just a flat Pack | Rename to `*_full.json` or `*_all.json` |
| Putting wiring notes in a Project | Projects track goals and blockers, not bench state | Put wiring in Bench Profile |
| One giant Pack with 12 tests and no stage structure | No gate between stages; if stage0 fails, stage2 still runs | Split into Suite → Pack per stage |
| Using "test" to mean "pack" in CLI commands | Confusing; `ael run --test` vs `ael pack --pack` | Follow the table above |

---

## Open Questions (for review)

1. **Should `suites/` directory be created now, or remain a naming convention?**
   Current state: suite structure exists only as naming convention (`_stage0/1/2`). No suite file format or `ael suite` command exists.

2. **What is the right `gate` default?** `stop_on_stage_fail` seems correct for hardware bring-up (no point running stage2 if stage1 fails). `run_all` might be useful for regression runs.

3. **Should `rp2040_s3jtag_full.json` be refactored into a proper Suite + 3 Packs?** It currently conflates Stage 0/1/2 into one flat Pack. This makes it impossible to re-run just Stage 2 after a wiring change.

4. **Should Pack carry a `stage` integer field?** This would allow the runtime to enforce ordering without a separate Suite file (e.g., refuse to run stage2 if stage1 has no passing run in the current session).

5. **Should Suite be runnable independently, or always via Project?** Argument for independent: useful for CI. Argument for via Project: ensures evidence is captured in one place.
