# STM32F411CEU6 I2C Loopback Debug Report

**Date:** 2026-03-29
**Test:** `tests/plans/stm32f411ceu6_i2c_loopback.json`
**Status:** RESOLVED — root cause was board hardware failure (Board A). Passes on Board B without external pull-ups.

---

## 1. Test Configuration

- **I2C1 master:** PB6 = SCL (AF4), PB7 = SDA (AF4)
- **I2C2 slave:** PB10 = SCL (AF4), PB3 = SDA (AF9)
- **Physical wiring:** PB6↔PB10 (SCL wire), PB7↔PB3 (SDA wire)
- **Pull-up:** STM32 internal ~40 kΩ (PUPDR=01 on all 4 pins), no external resistors
- **Speed:** SM 100 kHz (CCR=80)
- **Protocol:** Master writes 4 bytes {0xA1, 0xB2, 0xC3, 0xD4} to slave address 0x42, then reads them back

---

## 2. Original Symptom (Board A)

Mailbox consistently reported:
```
status     = 3 (FAIL)
error_code = 2 (ERR_SWRITE_ADDR)
detail0    = 0x04000200
```

| Field | Value | Meaning |
|-------|-------|---------|
| I2C2_SR1[7:0] | 0x00 | ADDR flag never set (slave did not match address) |
| I2C2_SR2[7:0] | 0x02 | BUSY=1 (slave detected START) |
| I2C1_SR1[15:0] | 0x0400 | AF=1 (master received NACK) |

---

## 3. Software Verified Correct (Board A)

All registers confirmed via SRAM diagnostic dump:

| Register | Expected | Actual | Status |
|----------|----------|--------|--------|
| I2C2_OAR1 | 0x4084 (addr 0x42, bit14=1) | 0x4084 | ✓ |
| I2C2_CR1 | 0x0401 (PE=1, ACK=1) | 0x0401 | ✓ |
| GPIOB_AFRL | 0x44009000 (PB7=AF4, PB6=AF4, PB3=AF9) | 0x44009000 | ✓ |
| GPIOB_MODER | PB3/6/7/10 = AF(10) | 0x0020A280 | ✓ |
| GPIOB_PUPDR | PB3/6/7/10 = pull-up(01) | 0x00105140 | ✓ |

---

## 4. Diagnostic Findings (Board A)

### 4.1 GPIO Wire Continuity Scan

wire_scan firmware (drive PB7 LOW, read entire GPIOB_IDR):
```
RES0 (PB7=HIGH): 0x0000f7ef
RES1 (PB7=LOW):  0x0000f76f
RES2 (XOR/diff): 0x00000080  ← only bit 7 (PB7 itself)
```

**Only PB7 itself changed.** PB3 (bit 3) stayed HIGH in both states → SDA wire had no electrical effect. SCL wire (PB6↔PB10) confirmed good.

Wire replacement attempted multiple times — same result. SDA wire appeared intact visually but electrically open.

### 4.2 Root Cause Identified: Board Hardware Failure

Stage 0–3 golden suite (19/19) ran successfully on Board A confirming SWD and PA/USART/SPI/ADC/EXTI all work. PC13 LED did NOT blink (should blink at 0.5–2 Hz) — confirming PC and PB GPIO hardware damage on Board A.

---

## 5. Resolution: Board B

Switched to a second STM32F411CEU6 BlackPill (Board B):

- Stage 0 blinky: LED blinks correctly ✓
- Full golden suite 19/19 PASS ✓
- **I2C loopback PASS** — no external pull-ups, jumper wire only ✓

**Conclusion:** Internal STM32F4 pull-ups (~40 kΩ) are sufficient for I2C SM 100 kHz loopback with a short jumper wire. No external pull-ups required.

Board A diagnosis: GPIO port B/C hardware damage (likely ESD or over-voltage event). SDA wire was not the cause.

---

## 6. Lessons Learned

| # | Lesson | CE ID |
|---|--------|-------|
| 1 | STM32F4 internal pull-ups sufficient for I2C loopback SM 100kHz | `6bef776a` |
| 2 | [HIGH_PRIORITY] Board swap is the fastest way to distinguish HW failure from SW bug | `94ac00dd` |
| 3 | [HIGH_PRIORITY] wire_scan IDR technique: drive output LOW, XOR full IDR high vs low = connected pins | `df19dd7c` |
| 4 | [HIGH_PRIORITY] BMDA: never `continue&` + `disconnect` — use `load + attach 1 + detach` | `77469dc5` |

---

## 7. Golden Suite Status

`stm32f411ceu6_i2c_loopback` re-added to golden suite. Total: **20/20 tests** on Board B.
