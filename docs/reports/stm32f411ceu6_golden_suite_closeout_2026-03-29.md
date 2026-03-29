# STM32F411CEU6 Golden Test Suite — Closeout Report

**Date:** 2026-03-29
**Pack:** `packs/stm32f411ceu6_golden.json`
**Result:** PASS — 19/19 tests

---

## 1. Suite Overview

| Stage | Tests | Count | Result |
|-------|-------|-------|--------|
| Stage 0 | pc13_blinky_visual, minimal_runtime_mailbox | 2 | ✓ PASS |
| Stage 1 | timer_mailbox, internal_temp_mailbox | 2 | ✓ PASS |
| Stage 2 | wiring_verify, exti_trigger, pwm_capture, uart_multibyte, spi_loopback, uart_dma, iwdg | 7 | ✓ PASS |
| Stage 3 | gpio_signature, gpio_loopback_banner, exti_banner, capture_banner, pwm_banner, uart_loopback_banner, spi_banner, adc_banner | 8 | ✓ PASS |
| **Total** | | **19** | **19/19 PASS** |

**Excluded:** `stm32f411ceu6_i2c_loopback` — hardware issue (SDA wire anomaly). See `docs/reports/stm32f411ceu6_i2c_loopback_debug_2026-03-29.md`.

---

## 2. Board & Bench Configuration

- **Board:** STM32F411CEU6 WeAct Black Pill V2.0
- **Instrument:** esp32jtag @ 192.168.2.103:4242
- **Bench profile:** `stm32f411ceu6__stage3`

### Wiring

| Net | Connection | Purpose |
|-----|-----------|---------|
| PA8 ↔ PA6 | jumper | GPIO / EXTI loopback |
| PA9 ↔ PA10 | jumper | USART1 TX↔RX loopback |
| PB0 ↔ PB1 | jumper | ADC/PWM loopback |
| PB15 ↔ PB14 | jumper | SPI2 MOSI↔MISO loopback |
| PB6 ↔ PB10 | jumper | I2C SCL (preserved, not used in suite) |
| PB7 ↔ PB3 | jumper | I2C SDA (preserved, not used in suite) |
| PA2 → P0.0 | LA probe | USART2 TX capture |
| PA3 → P0.1 | LA probe | USART2 RX capture |
| PB13 → P0.2 | LA probe | SPI2 SCK capture |
| GND → probe GND | wire | LA ground reference |

---

## 3. Key Milestones During Bring-up

### 3.1 Stage 0 / Mailbox Runtime
- Established mailbox protocol at `0x2000FC00` (magic=0xAE100001)
- Confirmed GDB-based flash + readback via BMDA/openocd over TCP (192.168.2.103:4242)
- GDB connection: `target extended-remote 192.168.2.103:4242` → `monitor swdp_scan` → `attach 1`

### 3.2 STM32 I2C Stuck-BUSY Fix (HIGH_PRIORITY — exp `db885cac`)
- GDB reset leaves I2C peripheral with stale BUSY flag set
- Fix: assert `I2C_CR1_SWRST` before any I2C config, wait 1 ms, clear SWRST, then configure
- Applied in `stm32f411ceu6_i2c_loopback/main.c` and recorded as cross-board pattern

### 3.3 F411 I2C PE-then-ACK Sequence
- Setting PE and ACK simultaneously on F411 causes SCL stretch before first START
- Fix: set PE first, do a dummy read of CR1, then set ACK, do another dummy read, delay 2 ms
- Specific to STM32F4 I2C peripheral (not an issue on F1 or H7)

### 3.4 I2C OAR1 Bit14
- F411 I2C OAR1 bit14 must always be written as 1 (reserved but required per RM0383)
- Encoding: `OAR1 = (addr << 1) | (1u << 14u)` — for addr 0x42: OAR1 = 0x4084

### 3.5 Stage 3 LA-Verified Banner Tests
- All 8 LA-verified banner tests passed on first attempt with Stage 3 bench profile
- LA preflight (internal signal self-test) confirmed working before each capture test

### 3.6 I2C Loopback — Suspended
- I2C loopback test never passed; diagnosed as hardware SDA wire issue
- Wire continuity test: PB7 driven LOW, PB3 remains HIGH → wire open/high resistance
- All software registers verified correct via SRAM diagnostic dump
- Test preserved in `tests/plans/` and `firmware/targets/`, removed from golden suite
- Full debug report: `docs/reports/stm32f411ceu6_i2c_loopback_debug_2026-03-29.md`

---

## 4. Open Issues / Future Work

| Item | Priority | Notes |
|------|----------|-------|
| I2C loopback hardware fix | Medium | Replace SDA jumper wire; add external 4.7kΩ pull-ups on SDA+SCL; consider PB9 instead of PB3 |
| I2C LA capture | Medium | Add P0.3=SDA, P0.4=SCL probes once hardware fixed; update bench profile and test plan |

---

## 5. Civilization Engine Audit

**Queries:** `stm32f411ceu6`, `HIGH_PRIORITY`
**Hits:** `db885cac` (I2C SWRST pattern) — applied
**New records (board_family):**
- F411 I2C PE-then-ACK timing sequence
- F411 I2C OAR1 bit14 encoding requirement
- SRAM diagnostic dump technique for bare-metal register verification
- GPIO wire continuity test method
