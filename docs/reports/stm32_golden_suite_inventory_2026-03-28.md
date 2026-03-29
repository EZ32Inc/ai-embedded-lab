# STM32 Golden Test Suite Inventory
**Date:** 2026-03-28
**Source:** `ael/civilization/data/run_index.json` + `assets_golden/duts/*/manifest.yaml` + `packs/`

---

## Summary

| Board | Family | Lifecycle | Tests | Verified | Pack(s) |
|-------|--------|-----------|------:|----------|---------|
| stm32f103_gpio | F1 | **golden** | 6 | 2026-03-13 | smoke_stm32, smoke_stm32f103_gpio_loopbacks_esp32jtag |
| stm32f103_gpio_stlink | F1 | — | 6 | — | smoke_stm32f103_gpio_loopbacks_stlink |
| stm32f103c6t6_bluepill_like | F1 | — | 2 | — | smoke_stm32f103c6_minimal |
| stm32f103rct6 | F1 | draft | 7 | — | smoke_stm32f103rct6, smoke_stm32f103rct6_mailbox_esp32jtag |
| stm32f103rct6_stlink | F1 | — | 7 | — | smoke_stm32f103rct6_stlink, smoke_stm32f103rct6_mailbox_stlink |
| stm32f401ce_blackpill | F4 | — | 1 | — | none (pre-golden) |
| stm32f401rct6 | F4 | **golden** | 13 | 2026-03-15 | smoke_stm32f401, stm32f401rct6_stage0, stm32f401rct6_stage0_mailbox, stm32f401rct6_stage1 |
| stm32f407_discovery | F4 | **golden** | 7 | 2026-03-18 | smoke_stm32f407, smoke_stm32f407_mailbox_stlink |
| stm32f407_discovery_esp32jtag | F4 | — | 1 | — | smoke_stm32f407_mailbox_esp32jtag |
| stm32f411ceu6 | F4 | **golden** | 8 | 2026-03-14 | smoke_stm32f411, stm32f411_full_suite |
| stm32g431cbu6 | G4 | **golden** | 10 | 2026-03-16 | smoke_stm32g431 |
| stm32h750vbt6 | H7 | **golden** | 7 | 2026-03-16 | smoke_stm32h750 |

**Total: 12 boards, 75 test entries**

---

## Board Details

### stm32f103_gpio — STM32F103C8T6 Bluepill GPIO Bench
- **Lifecycle:** golden | **Verified:** 2026-03-13
- **Instrument:** ESP32JTAG (primary), ST-Link (via stm32f103_gpio_stlink)
- **Tests (6):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f103_gpio_signature | 1/0 | 0.5 |
| stm32f103_gpio_no_external_capture | 1/0 | 0.5 |
| stm32f103_uart_loopback_mailbox | 1/0 | 0.5 |
| stm32f103_spi_mailbox | 1/0 | 0.5 |
| stm32f103_exti_mailbox | 1/0 | 0.5 |
| stm32f103_adc_mailbox | 1/0 | 0.5 |

---

### stm32f103_gpio_stlink — STM32F103 Bluepill via ST-Link
- **Lifecycle:** — (instrument variant of stm32f103_gpio)
- **Instrument:** ST-Link
- **Tests (6):** same as stm32f103_gpio + `stm32f103_gpio_no_external_capture_stlink` (stlink-specific variant)

---

### stm32f103c6t6_bluepill_like — STM32F103C6T6 Bluepill-like
- **Lifecycle:** — | **Pack:** smoke_stm32f103c6_minimal
- **Tests (2):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f103c6_gpio_no_external_capture | 12/0 | 1.0 |
| stm32f103c6_pc13_blinky_visual | 1/0 | 0.5 |

> **Note:** `gpio_no_external_capture` is the most battle-tested test in the entire STM32 inventory — 12 successful runs, confidence 1.0.

---

### stm32f103rct6 — STM32F103RCT6
- **Lifecycle:** draft | **Instrument:** ESP32JTAG (primary), ST-Link (via stm32f103rct6_stlink)
- **Tests (7):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f103rct6_mailbox | 1/0 | 0.5 |
| stm32f103rct6_timer_mailbox | 1/0 | 0.5 |
| stm32f103rct6_gpio_loopback | 1/0 | 0.5 |
| stm32f103rct6_uart_loopback | 1/0 | 0.5 |
| stm32f103rct6_exti_trigger | 1/0 | 0.5 |
| stm32f103rct6_adc_loopback | 1/0 | 0.5 |
| stm32f103rct6_spi_loopback | 1/0 | 0.5 |

---

### stm32f401ce_blackpill — STM32F401CE WeAct Black Pill
- **Lifecycle:** pre-golden (no manifest lifecycle stage, no pack)
- **Tests (1):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f401ce_led_blink | 2/3 | 0.6 |

> **Note:** Unstable — more failures than passes accumulated. Needs stabilisation before promotion.

---

### stm32f401rct6 — STM32F401RCT6
- **Lifecycle:** golden | **Verified:** 2026-03-15 | **Instrument:** ESP32JTAG
- **Tests (13):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f401_led_blink | 5/2 | 0.9 |
| stm32f401_gpio_signature | 1/0 | 0.5 |
| stm32f401_uart_loopback_banner | 1/0 | 0.5 |
| stm32f401_spi_banner | 1/0 | 0.5 |
| stm32f401_adc_banner | 1/0 | 0.5 |
| stm32f401_capture_banner | 1/0 | 0.5 |
| stm32f401_exti_banner | 1/0 | 0.5 |
| stm32f401_gpio_loopback_banner | 1/0 | 0.5 |
| stm32f401_pwm_banner | 1/0 | 0.5 |
| stm32f401rct6_internal_temp_mailbox | 1/0 | 0.5 |
| stm32f401rct6_minimal_runtime_mailbox | 1/0 | 0.5 |
| stm32f401rct6_pc13_blinky_visual | 1/1 | 0.5 |
| stm32f401rct6_timer_mailbox | 1/1 | 0.5 |

---

### stm32f407_discovery — STM32F4 Discovery (STM32F407VGT6)
- **Lifecycle:** golden | **Verified:** 2026-03-18 | **Instrument:** ST-Link (on-board), ESP32JTAG (via stm32f407_discovery_esp32jtag)
- **Tests (7):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f407_mailbox | 1/0 | 0.5 |
| stm32f407_timer_mailbox | 1/0 | 0.5 |
| stm32f407_gpio_loopback | 1/0 | 0.5 |
| stm32f407_uart_loopback | 1/0 | 0.5 |
| stm32f407_exti_trigger | 1/0 | 0.5 |
| stm32f407_adc_loopback | 1/0 | 0.5 |
| stm32f407_spi_loopback | 1/0 | 0.5 |

---

### stm32f411ceu6 — STM32F411CEU6 WeAct Black Pill V2.0
- **Lifecycle:** golden | **Verified:** 2026-03-14 | **Instrument:** ESP32JTAG
- **Tests (8):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32f411_gpio_signature | 1/0 | 0.5 |
| stm32f411_uart_loopback_banner | 1/0 | 0.5 |
| stm32f411_adc_banner | 1/0 | 0.5 |
| stm32f411_spi_banner | 1/0 | 0.5 |
| stm32f411_gpio_loopback_banner | 1/0 | 0.5 |
| stm32f411_pwm_banner | 1/0 | 0.5 |
| stm32f411_exti_banner | 1/0 | 0.5 |
| stm32f411_capture_banner | 1/0 | 0.5 |

---

### stm32g431cbu6 — STM32G431CBU6
- **Lifecycle:** golden | **Verified:** 2026-03-16 | **Instrument:** ESP32JTAG
- **Tests (10):** — most mature board in the STM32 inventory

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32g431_gpio_signature | 3/0 | 0.7 |
| stm32g431_minimal_runtime_mailbox | 3/0 | 0.7 |
| stm32g431_gpio_loopback | 2/0 | 0.6 |
| stm32g431_uart_loopback | 2/0 | 0.6 |
| stm32g431_spi | 2/0 | 0.6 |
| stm32g431_adc | 2/0 | 0.6 |
| stm32g431_pwm | 2/0 | 0.6 |
| stm32g431_exti | 2/0 | 0.6 |
| stm32g431_capture | 2/0 | 0.6 |
| unknown | 1/0 | 0.5 |

---

### stm32h750vbt6 — STM32H750VBT6 YD
- **Lifecycle:** golden | **Verified:** 2026-03-16 | **Instrument:** ESP32JTAG
- **Tests (7):**

| Test | success/fail | confidence |
|------|-------------|-----------|
| stm32h750_wiring_verify | 1/0 | 0.5 |
| stm32h750_minimal_runtime_mailbox | 1/0 | 0.5 |
| stm32h750_gpio_loopback | 1/0 | 0.5 |
| stm32h750_uart_loopback | 1/0 | 0.5 |
| stm32h750_exti_trigger | 1/0 | 0.5 |
| stm32h750_adc_dac_loopback | 1/0 | 0.5 |
| stm32h750_pwm_capture | 1/0 | 0.5 |

---

## Observations & Known Issues

- **stm32g431cbu6** is the most mature board: highest confidence (0.7), multiple repeat runs, zero failures across all 9 pack tests.
- **stm32f401rct6** has the largest test surface (13 entries, 4 packs including staged bring-up) — reflects the most active development history.
- **stm32f401ce_blackpill** is unstable (2/3 on its only test) and has no pack — needs stabilisation before promotion to golden.
- **stm32f103rct6** is `draft` — pack and firmware exist but board not yet verified/promoted.
- `stm32g431cbu6` has one `unknown` entry in run_index — likely a stale or mis-recorded test name; can be cleaned up.

---

## Ongoing Refactoring

Refactoring of the STM32 test suite structure is in progress. The primary goals are to align pack definitions, test naming conventions, and run_index coverage across all boards.

**Current focus (in order):**

### 1. stm32f401rct6
The most complex STM32 board currently, with 4 packs (stage0, stage0_mailbox, stage1, smoke) and 13 test entries spanning two naming conventions (`_banner` suffix tests from smoke pack vs. mailbox-style tests from stage packs). Refactoring aims to:
- Consolidate naming convention (`_banner` vs. bare test names)
- Align stage packs with the final smoke pack structure
- Promote remaining low-confidence tests toward verified status

### 2. stm32f103c6t6_bluepill_like
Currently the only board with confidence 1.0 on a test (`gpio_no_external_capture`, 12/0). However its lifecycle stage is unset and it has no golden manifest. Refactoring aims to:
- Add a proper `assets_golden/duts/stm32f103c6t6_bluepill_like/manifest.yaml`
- Promote to `lifecycle_stage: golden`
- Expand the smoke pack beyond the current single visual test

---

*Generated by AEL Civilization Engine audit — 2026-03-28*
