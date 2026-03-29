# STM32 Golden Test Suite Spec v1

**Status:** Active
**Date:** 2026-03-29
**Reference implementation:** `stm32f401rct6` — `packs/stm32f401rct6_golden.json`
**Applies to:** All STM32 boards onboarded into AEL (F0/F1/F4/G4/H7 and future families)

---

## 1. Purpose

This spec defines the standard structure for a Golden Test Suite on any STM32
board. The goal is a reproducible, self-consistent, staged validation suite that:

- Proves the board is alive and the instrument can communicate (Stage 0)
- Proves on-chip peripherals work without external wires (Stage 1)
- Proves all routed peripheral pairs work via loopback (Stage 2)
- Provides independent LA-verified waveform evidence (Stage 3)

A board that passes all four stages is declared **golden** in AEL. The suite
can be run selectively by stage using `ael pack --stage`.

---

## 2. Stage Definitions

### Stage 0 — Board Health (no wiring required)

**Goal:** Confirm the board boots, the instrument can flash and read it, and
the mailbox communication mechanism works.

| Test | Type | What it proves |
|------|------|---------------|
| `<board>_pc13_blinky_visual` | `program_only` | Board boots, LED visible, instrument can flash |
| `<board>_minimal_runtime_mailbox` | `baremetal_mailbox` | Mailbox read/write round-trip succeeds |

**Pass criteria:** Both tests pass in isolation before any wires are connected.
**Wiring:** None.
**Failure action:** Do not proceed to Stage 1. Debug instrument connection,
flash path, or firmware startup.

---

### Stage 1 — No-Wire Peripheral Self-Tests

**Goal:** Verify on-chip peripherals that need no external stimulus.

| Test | Type | What it proves |
|------|------|---------------|
| `<board>_timer_mailbox` | `baremetal_mailbox` | Basic timer interrupt via NVIC (TIM3 or equivalent) |
| `<board>_internal_temp_mailbox` | `baremetal_mailbox` | Internal ADC temperature sensor readable |

**Pass criteria:** Both pass without any external wires.
**Wiring:** None (same setup as Stage 0).
**Note:** Timer test exercises APB1 clock enable, TIM base config, update
interrupt, NVIC delivery, and WFI. Temperature test exercises ADC clock,
internal channel, and conversion. These are the minimum functional indicators
of a healthy Cortex-M4/M3/M0 runtime.

---

### Stage 2 — External Loopback Mailbox Tests

**Goal:** Verify every routed peripheral pair using baremetal mailbox firmware.
The instrument only flashes and reads the mailbox — no LA required.

#### Standard loopback set (8 tests)

| Test | Peripheral | Wiring |
|------|-----------|--------|
| `<board>_wiring_verify` | GPIO + UART + ADC sanity | all stage2 wires |
| `<board>_exti_trigger` | EXTI (external interrupt) | GPIO pair |
| `<board>_pwm_capture` | TIM PWM output + TIM Input Capture | GPIO pair |
| `<board>_uart_multibyte` | USART TX→RX, multi-byte | UART pair |
| `<board>_spi_loopback` | SPI MOSI→MISO | SPI pair |
| `<board>_uart_dma` | USART + DMA TX→RX | UART pair (shared with uart_multibyte) |
| `<board>_iwdg` | IWDG / LSI watchdog | none (self-contained) |
| `<board>_i2c_loopback` | I2C master ↔ I2C slave | I2C SCL + SDA pairs |

#### Wiring conventions

- All wires stay on the bench for the entire stage2+3 run — never moved mid-suite.
- Use STM32 internal pull-ups (PUPDR=01, ~40 kΩ) for I2C; no external resistors required.
- If the default pin mapping is not available on the board connector, use the
  next valid alternate function (AF) mapping from the reference manual. Document
  the substitution in the test plan's `bench_setup.notes`.
- Typical wiring for F4-class boards (adapt pin names per board):

```
PA8  ↔ PA6    # GPIO out ↔ GPIO in / EXTI / PWM capture
PA9  ↔ PA10   # USART1 TX ↔ RX
PB0  ↔ PB1    # ADC loopback (analog)
PB15 ↔ PB14   # SPI MOSI ↔ MISO
PB6  ↔ PB10   # I2C SCL (master ↔ slave)
PB7  ↔ PB3    # I2C SDA (master ↔ slave, PB3 AF9 if PB11 not on connector)
```

#### Error code convention (mailbox)

Firmware must report structured errors via `ael_mailbox_fail(error_code, detail0)`.
Error codes must be non-bitmask sequential integers:
- 1–N: step-by-step timeout codes (which hardware step timed out)
- N+1: data mismatch (detail0 = number of bytes matched)

This allows the instrument to report the exact failing step without LA.

#### Known STM32 bare-metal pitfalls

| Pitfall | Fix | CE ID |
|---------|-----|-------|
| I2C BUSY stuck after GDB reset (SYSRESETREQ) | Assert SWRST (CR1 bit 15) + 1 ms delay before any I2C config | `db885cac` |
| Timer IRQ at wrong vector index | Expand vector table to `16 + IRQ_N`; verify against RM | — |
| I2C default pin not on connector | Use alternate AF mapping from RM Table 9; note in test plan | — |

---

### Stage 3 — LA-Verified Banner Tests

**Goal:** Provide independent instrument-side waveform evidence for each
peripheral. The LA captures the signal driven by the DUT firmware on a
dedicated output pin, verifying timing and shape without relying on the
mailbox return path alone.

#### Standard banner set (8 tests)

| Test | Signal | What LA verifies |
|------|--------|-----------------|
| `<board>_gpio_signature` | PA2 ~250 Hz, PA3 ~125 Hz | 2:1 frequency ratio, confirms clock |
| `<board>_gpio_loopback_banner` | PA2 edge train | GPIO loopback round-trip |
| `<board>_exti_banner` | PA2 pulse burst | EXTI interrupt count via output |
| `<board>_capture_banner` | PA2 input-capture driven output | TIM capture period |
| `<board>_pwm_banner` | PA2 PWM | Period and duty cycle |
| `<board>_uart_loopback_banner` | PA2 UART-driven output | UART frame received |
| `<board>_spi_banner` | PA2 SPI-driven output | SPI transfer complete |
| `<board>_adc_banner` | PA2 ADC-driven output | ADC conversion result |

#### LA wiring convention

```
PA2  → P0.0   # Primary proof signal (sig)
PA3  → P0.1   # Secondary / half-rate signal
PB13 → P0.2   # Auxiliary signal
GND  → probe GND
```

These three LA channels are defined in the bench profile
(`configs/bench_profiles/<board>__stage3.yaml`) under `observe_map`.

The firmware uses PA2 as its primary "banner output" — after completing a
peripheral operation, it pulses or toggles PA2 in a known pattern that the
instrument can count or time independently of the mailbox.

#### Bench profile requirements

```yaml
bench_profile:
  id: <board>__stage3
  observe_map:
    sig:  P0.0
    pa2:  P0.0
    pa3:  P0.1
    pb13: P0.2
  verification_views:
    signal:
      pin: sig
      resolved_to: P0.0
      description: Primary proof capture
    aux:
      pin: pb13
      resolved_to: P0.2
      description: Auxiliary observed pin
  default_wiring:
    swd: "P3"
    reset: "NC"
    verify: "P0.0"
```

---

## 3. Pack Structure

The Golden Suite pack must define both a flat `tests` list (for running all
stages) and a `stages` dict (for selective `--stage` filtering):

```json
{
  "name": "<board>_golden",
  "description": "...",
  "board": "<board_id>",
  "bench_profile": "<board>__stage3",
  "status": "golden",
  "verified_date": "YYYY-MM-DD",
  "stages": {
    "0": ["tests/plans/<board>_pc13_blinky_visual.json",
          "tests/plans/<board>_minimal_runtime_mailbox.json"],
    "1": ["tests/plans/<board>_timer_mailbox.json",
          "tests/plans/<board>_internal_temp_mailbox.json"],
    "2": ["tests/plans/<board>_wiring_verify.json",
          "tests/plans/<board>_exti_trigger.json",
          "tests/plans/<board>_pwm_capture.json",
          "tests/plans/<board>_uart_multibyte.json",
          "tests/plans/<board>_spi_loopback.json",
          "tests/plans/<board>_uart_dma.json",
          "tests/plans/<board>_iwdg.json",
          "tests/plans/<board>_i2c_loopback.json"],
    "3": ["tests/plans/<board>_gpio_signature.json",
          "tests/plans/<board>_gpio_loopback_banner.json",
          "tests/plans/<board>_exti_banner.json",
          "tests/plans/<board>_capture_banner.json",
          "tests/plans/<board>_pwm_banner.json",
          "tests/plans/<board>_uart_loopback_banner.json",
          "tests/plans/<board>_spi_banner.json",
          "tests/plans/<board>_adc_banner.json"]
  },
  "tests": [ /* flat union of all stages in order */ ]
}
```

Place at: `packs/<board>_golden.json`

---

## 4. DUT Manifest Requirements

`assets_golden/duts/<board>/manifest.yaml` must contain:

```yaml
lifecycle_stage: golden
default_packs:
  - packs/<board>_golden.json
verified:
  status: true
  verification_suite: <board>_golden
  tests: 20
  sequential_pass: true
  latest_run_id: <run_id>
  verified_on:
    bench_id: <instrument_instance_id>
    instrument_endpoint: <ip>:<port>
  date: <YYYY-MM-DD>
  experiments_passed: 20
  golden_pack: packs/<board>_golden.json
  golden_covers:
    - pc13_blinky_visual
    - minimal_runtime_mailbox
    - timer_mailbox
    - internal_temp_mailbox
    - wiring_verify
    - exti_trigger
    - pwm_capture
    - uart_multibyte
    - spi_loopback
    - uart_dma
    - iwdg
    - i2c_loopback
    - gpio_signature
    - gpio_loopback_banner
    - exti_banner
    - capture_banner
    - pwm_banner
    - uart_loopback_banner
    - spi_banner
    - adc_banner
```

---

## 5. Firmware Requirements

### Mailbox address

All mailbox tests must use: `0x2000FC00` (top of SRAM, board-agnostic for
STM32 targets with ≥64 KB SRAM). Defined in `ael/mailbox_contract.h`.

### Toolchain

- Cross-compiler: `arm-none-eabi-gcc`
- Optimization: `-O1` or `-Os` (never `-O0` — timing-sensitive)
- No HAL / no RTOS — pure register-level bare metal
- Startup: minimal vector table (`isr_vector`) + `SystemInit` stub
- Clock: HSI 16 MHz (F4) or HSI 8 MHz (F1) unless test explicitly requires HSE

### Firmware structure per test

```
firmware/targets/<board>_<test_name>/
  main.c       # test logic + ael_mailbox_pass/fail()
  Makefile     # builds to artifacts/build_<board>_<test_name>/<artifact_stem>.elf
  startup.s    # (optional, if not shared)
  linker.ld    # (optional, if not shared)
```

### Shared firmware across stages

Stage 2 and Stage 3 tests for the same peripheral may share a firmware binary
if the banner output (PA2) is always driven regardless of result path. Shared
firmware must be explicitly noted in `test_plan.build.project_dir`.

---

## 6. Test Plan Schema Requirements

Every test plan (`tests/plans/<board>_<name>.json`) must conform to
`ael/test_plan_schema.py` and include:

```json
{
  "schema_version": "1.0",
  "test_kind": "baremetal_mailbox",
  "name": "<board>_<name>",
  "board": "<board_id>",
  "supported_instruments": ["esp32jtag"],
  "requires": { "mailbox": true, "datacapture": false },
  "labels": ["mailbox", "portable"],
  "covers": ["<peripheral_a>", "<peripheral_b>"],
  "build": {
    "project_dir": "firmware/targets/<board>_<name>",
    "artifact_stem": "<board>_<name>_app",
    "build_dir": "artifacts/build_<board>_<name>"
  },
  "signal_checks": [],
  "mailbox_verify": { "settle_s": 5.0, "addr": "0x2000FC00" },
  "bench_setup": {
    "notes": "<wiring description, peripheral roles, error code table>",
    "peripheral_signals": [
      { "role": "<ROLE>", "dut_signal": "<PIN>", "direction": "<in|out|bidir>", "notes": "..." }
    ]
  }
}
```

`datacapture: false` for all Stage 0/1/2 tests.
`settle_s: 5.0` is the default; increase to 10.0 for tests involving PLL lock
or watchdog timeout sequences.

---

## 7. Bench Profile Requirements

One bench profile covers Stage 2 and Stage 3 (same physical wiring):

```yaml
bench_profile:
  id: <board>__stage3
  board_id: <board_id>
  description: "Stage2/3 wiring: <loopback pairs>, LA on P0.0/P0.1/P0.2"

  bench_connections:
    - { from: PA8,  to: PA6   }   # GPIO/EXTI/PWM loopback
    - { from: PA9,  to: PA10  }   # UART
    - { from: PB0,  to: PB1   }   # ADC
    - { from: PB15, to: PB14  }   # SPI
    - { from: PB6,  to: PB10  }   # I2C SCL
    - { from: PB7,  to: PB3   }   # I2C SDA
    - { from: PA2,  to: P0.0  }   # LA primary
    - { from: PA3,  to: P0.1  }   # LA secondary
    - { from: PB13, to: P0.2  }   # LA auxiliary
    - { from: GND,  to: probe GND }

  safe_pins: [ PA2, PA3, PA6, PA8, PA9, PA10, PB0, PB1, PB3,
               PB6, PB7, PB10, PB13, PB14, PB15, PC13 ]
```

Place at: `configs/bench_profiles/<board>__stage3.yaml`

---

## 8. Run Commands

```bash
# Full golden suite
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id>

# Single stage
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 0
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 1
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 2
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 3

# Multiple stages
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 0,1
python3 -m ael pack --pack packs/<board>_golden.json --board <board_id> --stage 2,3
```

---

## 9. Promotion Criteria

A board is promoted to `lifecycle_stage: golden` when:

1. All Stage 0 tests pass (minimum to merge any firmware)
2. All Stage 1 tests pass (minimum to claim peripheral health)
3. All Stage 2 tests pass in a single `ael pack` run (no cherry-picks)
4. All Stage 3 tests pass in a single `ael pack` run
5. `assets_golden/duts/<board>/manifest.yaml` updated with `verified.status: true`
6. `packs/<board>_golden.json` committed with `"status": "golden"`
7. Closeout report written to `docs/reports/<board>_golden_suite_closeout_<date>.md`
8. run_index updated for all 20 tests

---

## 10. Adaptation for Other MCU Families

This spec targets STM32 Cortex-M. When adapting for other families:

| Parameter | STM32 F4 | STM32 F1 | STM32 G4 | STM32 H7 | Other MCU |
|-----------|----------|----------|----------|----------|-----------|
| Mailbox addr | `0x2000FC00` | `0x20004C00` | `0x2000FC00` | `0x2001FC00` | top of SRAM |
| HSI clock | 16 MHz | 8 MHz | 16 MHz | 64 MHz | per datasheet |
| I2C SWRST needed | Yes | Yes | Yes | Yes | check RM |
| Stage3 signal pin | PA2 | PA2 | PA2 | PA2 | any free GPIO |
| I2C SDA alternate | PB3 AF9 (if PB11 N/A) | PB7 AF | PB7 AF | — | check RM |

For non-STM32 MCUs (ESP32, RP2040, etc.), replace the mailbox contract with
the platform-equivalent IPC mechanism and adapt the firmware toolchain section.
The four-stage structure (health → self-test → loopback → LA-verify) remains
applicable regardless of MCU family.

---

## 11. Reference Files

| File | Role |
|------|------|
| `packs/stm32f401rct6_golden.json` | Reference pack (canonical implementation) |
| `configs/bench_profiles/stm32f401rct6__stage3.yaml` | Reference bench profile |
| `assets_golden/duts/stm32f401rct6/manifest.yaml` | Reference DUT manifest |
| `firmware/targets/stm32f401rct6_i2c_loopback/main.c` | Reference Stage 2 firmware (I2C, SWRST pattern) |
| `tests/plans/stm32f401rct6_i2c_loopback.json` | Reference test plan |
| `docs/reports/stm32f401rct6_golden_suite_closeout_2026-03-29.md` | Reference closeout report |
| `ael/test_plan_schema.py` | Test plan validator |
| `ael/pack_loader.py` | Pack loader |
| `ael/__main__.py` (`run_pack`) | Pack runner with `--stage` support |
