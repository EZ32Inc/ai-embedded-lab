# STM32G431CBU6 Golden Test Suite — Closeout Report

**Date:** 2026-03-29
**Pack:** `packs/stm32g431cbu6_golden.json`
**Result:** PASS — 14/14 tests

---

## 1. Suite Overview

| Stage | Tests | Count | Result |
|-------|-------|-------|--------|
| Stage 0 | blinky_visual, minimal_runtime_mailbox | 2 | ✓ PASS |
| Stage 1 | timer_mailbox, internal_temp_mailbox | 2 | ✓ PASS |
| Stage 2 | wiring_verify, iwdg, exti, capture, uart_loopback, spi | 6 | ✓ PASS |
| Stage 3 | gpio_signature, gpio_loopback, pwm, adc | 4 | ✓ PASS |
| **Total** | | **14** | **14/14 PASS** |

---

## 2. Board & Bench Configuration

- **Board:** STM32G431CBU6 (WeAct or equivalent, UFQFPN48)
- **Instrument:** esp32jtag_g431_bench @ 192.168.2.111:4242
- **Bench profile:** `stm32g431cbu6__default`

### Wiring

| Net | Connection | Purpose |
|-----|-----------|---------|
| PA8 ↔ PA6 | jumper | GPIO/EXTI/PWM/capture loopback |
| PA9 ↔ PA10 | jumper | USART1 TX↔RX loopback |
| PB4 ↔ PB5 | jumper | SPI1 MISO↔MOSI loopback |
| PB1 ↔ PB0 | jumper | ADC loopback (PB1 drive → PB0 ADC1_IN15) |
| PA2 → P0.3 | LA probe | Primary signal capture |
| PA3 → P0.0 | LA probe | Secondary signal (PA3 half-rate) |
| PA4 → P0.2 | LA probe | Auxiliary capture (capture/PWM) |
| PB3 → P0.1 | LA probe | SPI SCK capture |
| GND → probe GND | wire | LA ground reference |

---

## 3. New Firmware Created

| Firmware | Purpose |
|---------|---------|
| `stm32g431_timer_mailbox` | TIM3 IRQ test (Stage 1, no-wire) |
| `stm32g431_internal_temp_mailbox` | ADC1 internal temperature sensor (Stage 1, no-wire) |
| `stm32g431_wiring_verify` | GPIO/UART/ADC loopback wiring check (Stage 2) |
| `stm32g431_iwdg` | IWDG + LSI oscillator test (Stage 2) |

---

## 4. Key Technical Notes

### 4.1 G431 Startup Vector Table
The shared `stm32g431cbu6/startup.c` only defines the 16 core exception vectors.
For `timer_mailbox`, a local `startup.c` was created including vendor IRQs 0–29 with `TIM3_IRQHandler` at position IRQ29. TIM3 is IRQ29 on G431, same as F411.

### 4.2 G431 ADC Differences from F411
- ADC1 base: `0x50000000` (AHB2-2 bus), not `0x40012000` (APB2 like F4)
- Requires `DEEPPWD` clear → `ADVREGEN` → calibration → `ADEN` sequence
- Internal temperature: channel IN16 (not CH18 on F4), enabled by `ADC12_CCR` `VSENSESEL` (bit 22)
- `CKMODE=01` (bits[17:16] of `ADC12_CCR`) for synchronous HCLK clock

### 4.3 G431 RCC Differences
- `RCC_APB1ENR1` at `RCC_BASE+0x58` (bit1=TIM3EN)
- `RCC_APB2ENR` at `RCC_BASE+0x60` (bit14=USART1EN)
- `RCC_AHB2ENR` at `RCC_BASE+0x4C` (bit0=GPIOAEN, bit1=GPIOBEN, bit13=ADC12EN)
- `RCC_CSR` at `RCC_BASE+0x94` (LSION=bit0, LSIRDY=bit1) — note: offset differs from F4's `+0x74`

### 4.4 G431 USART1 New-Style
USART1 at `0x40013800` uses new-style G4 register map: `ISR/ICR/RDR/TDR` (no legacy `SR/DR`).
BRR=139 for 115200 @ 16 MHz HSI.

---

## 5. Civilization Engine Audit

**Queries performed:** `stm32g431cbu6`, `HIGH_PRIORITY`, `timer`, `adc`, `iwdg`
**Hits applied:** none — first G431 suite, no prior patterns blocked

**New records:**
| ID | Scope | Lesson |
|----|-------|--------|
| `fe733fd5` | board_family | [HIGH_PRIORITY] G431 TIM3 IRQ needs local startup.c with vendor vectors |
| `2122b0dc` | board_family | G431 ADC1 at 0x50000000, CH16 internal temp, ADVREGEN sequence |
| `2b5c77a7` | board_family | G431 IWDG RCC_CSR at +0x94, APB1ENR1 at +0x58 |
| `8bc5a7c0` | task | G431 golden suite 14/14 PASS — full wiring and firmware record |
