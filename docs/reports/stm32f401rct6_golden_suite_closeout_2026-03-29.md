# STM32F401RCT6 Golden Test Suite Closeout

**Date:** 2026-03-29
**Board:** `stm32f401rct6` (WeAct BlackPill, STM32F401RCT6, Cortex-M4 @ 16 MHz HSI)
**Pack:** `packs/stm32f401rct6_golden.json`
**Instrument:** `esp32jtag_blackpill_192_168_2_106` @ 192.168.2.106:4242
**Status:** ✓ GOLDEN — all 20 tests PASS

---

## Summary

STM32F401RCT6 is the first STM32 board in AEL to achieve a complete four-stage
Golden Test Suite, covering board health, no-wire peripheral self-tests,
external loopback verification, and independent LA signal capture. All 20 tests
passed in a single `ael pack` run on 2026-03-29.

This suite serves as the reference model for Golden Suite construction on all
other STM32 boards. See `docs/specs/stm32_golden_suite_spec_v1.md`.

---

## Wiring

| Wire | Connects |
|------|----------|
| PA8 ↔ PA6 | GPIO/EXTI/PWM loopback |
| PA9 ↔ PA10 | USART1 TX/RX loopback |
| PB0 ↔ PB1 | ADC loopback |
| PB15 ↔ PB14 | SPI2 MOSI/MISO loopback |
| PB6 ↔ PB10 | I2C1_SCL ↔ I2C2_SCL |
| PB7 ↔ PB3 | I2C1_SDA ↔ I2C2_SDA (PB3 AF9, alternate because PB11 not on connector) |
| PA2 → P0.0 | LA ch0 — primary signal capture |
| PA3 → P0.1 | LA ch1 — half-rate signal |
| PB13 → P0.2 | LA ch2 — auxiliary |
| GND → probe GND | Reference |

Total: 6 loopback jumper wires + 3 LA probe wires + GND.

---

## Test Results

### Stage 0 — Board Health (2 tests, no wiring required)

| Test | Run ID | Result |
|------|--------|--------|
| `stm32f401rct6_pc13_blinky_visual` | 2026-03-29_06-21-35 | **PASS** |
| `stm32f401rct6_minimal_runtime_mailbox` | 2026-03-29 | **PASS** |

Proves: firmware boots, PC13 LED toggles, mailbox communication works.

### Stage 1 — No-Wire Peripheral Self-Tests (2 tests)

| Test | Run ID | Result |
|------|--------|--------|
| `stm32f401rct6_timer_mailbox` | 2026-03-29 | **PASS** |
| `stm32f401rct6_internal_temp_mailbox` | 2026-03-29 | **PASS** |

Proves: TIM3 interrupt delivery via NVIC, internal ADC temperature sensor.

### Stage 2 — External Loopback Mailbox Tests (8 tests)

| Test | Peripheral | Result |
|------|-----------|--------|
| `stm32f401rct6_wiring_verify` | GPIO + UART + ADC wiring sanity | **PASS** |
| `stm32f401rct6_exti_trigger` | EXTI6 on PA6 (10 rising edges from PA8) | **PASS** |
| `stm32f401rct6_pwm_capture` | TIM1 PWM (PA8) → TIM3 Input Capture (PA6) | **PASS** |
| `stm32f401rct6_uart_multibyte` | USART1 PA9→PA10, 115200 8N1, multi-byte | **PASS** |
| `stm32f401rct6_spi_loopback` | SPI2 MOSI (PB15) → MISO (PB14) | **PASS** |
| `stm32f401rct6_uart_dma` | USART1 + DMA2, TX→RX loopback | **PASS** |
| `stm32f401rct6_iwdg` | IWDG/LSI, watchdog kick and deliberate timeout | **PASS** |
| `stm32f401rct6_i2c_loopback` | I2C1 master (PB6/PB7) ↔ I2C2 slave (PB10/PB3) | **PASS** |

Pack run ID: `2026-03-29_08-37-31` (full stage2 pack run)

### Stage 3 — LA-Verified Banner Tests (8 tests)

| Test | Signal Captured | Result |
|------|----------------|--------|
| `stm32f401_gpio_signature` | PA2 ~250 Hz, PA3 ~125 Hz (ratio check) | **PASS** |
| `stm32f401_gpio_loopback_banner` | PA2 loopback edge via PA6 | **PASS** |
| `stm32f401_exti_banner` | PA2 pulse train from EXTI | **PASS** |
| `stm32f401_capture_banner` | PA2 TIM1 PWM waveform | **PASS** |
| `stm32f401_pwm_banner` | PA2 PWM period/duty measurement | **PASS** |
| `stm32f401_uart_loopback_banner` | PA2 UART framing | **PASS** |
| `stm32f401_spi_banner` | PA2 SPI clock/data | **PASS** |
| `stm32f401_adc_banner` | PA2 ADC-driven output | **PASS** |

Run timestamps: 2026-03-29 06:25–06:29

---

## Notable Issues Encountered and Fixed

### 1. I2C BUSY flag stuck across GDB resets (CE: `db885cac`)

**Symptom:** I2C test failed immediately with error_code=1 (ERR_WRITE_SB — master
never generated START).

**Root cause:** STM32 I2C peripheral retains BUSY flag after SYSRESETREQ (GDB soft
reset). Master sees BUSY=1 and refuses to generate START.

**Fix:** Assert SWRST (I2C_CR1 bit 15) + delay 1 ms before configuring any I2C
peripheral. Required for both I2C1 and I2C2.

**Pattern:** Applies to all STM32 bare-metal I2C (F1/F4/F7/H7). Recorded as
`[HIGH_PRIORITY]` CE pattern `db885cac`.

### 2. PB11 not on BlackPill connector

**Symptom:** I2C2_SDA default mapping (PB11, AF4) is not exposed on the WeAct
BlackPill form factor.

**Fix:** Use PB3 (AF9) as alternate I2C2_SDA mapping. Confirmed valid on
STM32F401RCT6 reference manual.

### 3. ael run --pack vs ael pack (CE: `bb3a87f5`)

`ael run --pack` only runs a single test (ignores the `tests` array). Use
`ael pack` subcommand to run all tests in a pack.

---

## Pack and Asset Files

| File | Description |
|------|-------------|
| `packs/stm32f401rct6_golden.json` | Golden Suite pack (20 tests, `stages` field) |
| `assets_golden/duts/stm32f401rct6/manifest.yaml` | DUT manifest, `default_packs` updated |
| `configs/bench_profiles/stm32f401rct6__stage3.yaml` | Bench profile (loopback + LA wiring) |
| `tests/plans/stm32f401rct6_*.json` | Stage 0/1/2 test plans (mailbox) |
| `tests/plans/stm32f401_*_banner.json` | Stage 3 test plans (LA banner) |
| `firmware/targets/stm32f401rct6_*/` | Firmware targets for each test |

---

## How to Run

```bash
# Full golden suite (all 20 tests)
python3 -m ael pack --pack packs/stm32f401rct6_golden.json --board stm32f401rct6

# Stage 0 only (2 tests, no wiring)
python3 -m ael pack --pack packs/stm32f401rct6_golden.json --board stm32f401rct6 --stage 0

# Stage 0 + 1 (4 tests, no wiring)
python3 -m ael pack --pack packs/stm32f401rct6_golden.json --board stm32f401rct6 --stage 0,1

# Stage 2 only (8 loopback mailbox tests)
python3 -m ael pack --pack packs/stm32f401rct6_golden.json --board stm32f401rct6 --stage 2

# Stage 3 only (8 LA banner tests)
python3 -m ael pack --pack packs/stm32f401rct6_golden.json --board stm32f401rct6 --stage 3
```

---

## Civilization Engine Audit

| CE ID | Scope | Description |
|-------|-------|-------------|
| `db885cac` | pattern [HIGH_PRIORITY] | STM32 I2C BUSY stuck across GDB resets — assert SWRST before config |
| `bb3a87f5` | pattern [HIGH_PRIORITY] | `ael pack` vs `ael run --pack` — use pack subcommand for multi-test runs |
| `b6479757` | board_family | stm32f401rct6 stage2 pack 8/8 PASS, pack invocation command |

run_index updated for all 20 tests.
