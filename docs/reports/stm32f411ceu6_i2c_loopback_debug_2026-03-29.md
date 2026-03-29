# STM32F411CEU6 I2C Loopback Debug Report

**Date:** 2026-03-29
**Test:** `tests/plans/stm32f411ceu6_i2c_loopback.json`
**Status:** Suspended — hardware issue suspected. Removed from golden suite pending investigation.

---

## 1. Test Configuration

- **I2C1 master:** PB6 = SCL (AF4), PB7 = SDA (AF4)
- **I2C2 slave:** PB10 = SCL (AF4), PB3 = SDA (AF9)
- **Physical wiring:** PB6↔PB10 (SCL wire), PB7↔PB3 (SDA wire)
- **Pull-up:** STM32 internal ~40 kΩ (PUPDR=01 on all 4 pins), no external resistors
- **Speed:** SM 100 kHz (CCR=80); also tested at 10 kHz (CCR=800)
- **Protocol:** Master writes 4 bytes {0xA1, 0xB2, 0xC3, 0xD4} to slave address 0x42, then reads them back
- **Failure since:** First attempt; test has never passed on this board

---

## 2. Symptom

Mailbox consistently reports:
```
status     = 3 (FAIL)
error_code = 2 (ERR_SWRITE_ADDR)
detail0    = 0x04000200
```

Decoded:
| Field | Value | Meaning |
|-------|-------|---------|
| I2C2_SR1[7:0] | 0x00 | ADDR flag never set (slave did not match address) |
| I2C2_SR2[7:0] | 0x02 | BUSY=1 (I2C2 slave detected a START condition) |
| I2C1_SR1[15:0] | 0x0400 | AF=1 (master received NACK on address byte) |

**Interpretation:** Master (I2C1) sent START + address 0x42. Slave (I2C2) detected the START (BUSY=1) but the address was never matched (ADDR=0). Master received NACK and set AF flag.

---

## 3. What Was Verified (Software)

All software/register configuration was confirmed correct via SRAM diagnostic dump at 0x2000FC10 and 0x2000FC20:

| Register | Expected | Actual | Status |
|----------|----------|--------|--------|
| I2C2_OAR1 | 0x4084 (addr 0x42, bit14=1) | 0x4084 | ✓ |
| I2C2_CR1 | 0x0401 (PE=1, ACK=1) | 0x0401 | ✓ |
| GPIOB_AFRL | 0x44009000 (PB7=AF4, PB6=AF4, PB3=AF9) | 0x44009000 | ✓ |
| GPIOB_MODER | PB3/6/7/10 = AF(10) | 0x0020A280 ✓ | ✓ |
| GPIOB_PUPDR | PB3/6/7/10 = pull-up(01) | 0x00105140 ✓ | ✓ |
| I2C2_SR2 before START | 0x00 (BUSY=0) | 0x00 | ✓ |

Conclusions from software verification:
- OAR1 is correct: address 0x42 is properly encoded
- PE and ACK are set before START is generated
- GPIO alternate function, mode, and pull-up are all correct
- The bus is idle (BUSY=0) before the master generates START
- The SWRST is correctly applied (no stale BUSY)

---

## 4. Hypothesis Tests and Results

### 4.1 Pull-up too weak for 100 kHz (RULED OUT)

**Hypothesis:** 40 kΩ internal pull-up insufficient for 100 kHz; SDA rise time too slow → slave samples wrong bits.

**Test:** Reduced I2C speed to 10 kHz (CCR=800). At 10 kHz, RC rise time with 40 kΩ × 50 pF = 2 μs is well within the 50 μs half-period.

**Result:** Identical failure. Error code and detail0 unchanged.

**Conclusion:** Signal timing at 100 kHz is NOT the root cause.

### 4.2 Wrong AF number for PB3 (RULED OUT)

**Hypothesis:** AF9 is incorrect; maybe it should be AF8 or AF4.

**Test:** Compared STM32F411 DS10693 Table 9. Confirmed: PB3 → AF09 = I2C2_SDA. Column header "AF09 = I2C2/I2C3" verified. Also tested AF8 for PB3 → same failure.

**Conclusion:** AF9 is correct for PB3 → I2C2_SDA on STM32F411.

### 4.3 Wrong address in OAR1 (RULED OUT)

**Test:** Tried SLAVE_ADDR = 0x27 (different address). I2C2 OAR1 = 0x404E confirmed in SRAM dump. Same failure with ADDR=0.

**Conclusion:** No address-specific issue. I2C2 slave does not match ANY address.

### 4.4 JTAG/SWO interference on PB3 (INCONCLUSIVE)

**Hypothesis:** PB3 is the JTDO/SWO debug pin. Even though configured as AF9, the TPIU trace output might interfere.

**Test A:** Role-swap — configured I2C2 as master (PB10=SCL, PB3=SDA driving) and I2C1 as slave (PB6=SCL, PB7=SDA, a non-JTAG pin). Physical wiring unchanged.

**Result:** I2C1 slave (non-JTAG PB7) ALSO fails: ADDR=0, BUSY=1. I2C2 master reports ARLO (arbitration lost, bit9 of SR1) instead of AF. Both slaves fail identically.

**Conclusion:** The failure is NOT specific to PB3 as a JTAG pin. I2C1 slave on the non-JTAG PB7 pin also cannot match the address. This points to a physical bus problem rather than a software/peripheral configuration issue.

The ARLO on I2C2 master (role-swap) is significant: ARLO means the master drove SDA HIGH (released it) but sampled SDA as LOW. Something on the bus was pulling SDA down when the master expected it HIGH.

### 4.5 SDA wire continuity test (KEY FINDING)

A direct GPIO wire test was performed before any I2C init:
- PB7 temporarily configured as GPIO push-pull output
- PB3 temporarily configured as GPIO input (pull-up retained)
- GPIOB_BSRR used to drive PB7 LOW; PB3 IDR read after 1 ms delay

**Results (SRAM 0x2000FC30):**
```
wt[0] = 0x0000C388  GPIOB_IDR idle: PB3=1, PB7=1, PB10=0(?), PB6=0(?)
wt[1] = 0x00000001  PB3 when PB7 driven HIGH → 1 (expected 1, pull-up confirms)
wt[2] = 0x00000001  PB3 when PB7 driven LOW  → 1 (expected 0 — WIRE ANOMALY)
wt[3] = 0x00000000  PB6 when PB10 driven LOW → 0 (expected 0 — SCL wire OK ✓)
```

**SCL wire (PB6↔PB10): CONFIRMED GOOD** — wt[3]=0 as expected.

**SDA wire (PB7↔PB3): ANOMALOUS** — wt[2]=1, meaning PB3 remains HIGH when PB7 is actively driven LOW. For a good wire with 40 kΩ pull-up on PB3, driving PB7 to 0 V should pull PB3 well below VIL (0.99 V). That PB3 reads HIGH suggests:
- The wire between PB7 and PB3 is not connected, OR
- The wire has resistance > ~17 kΩ (extremely poor contact)

**Note on BUSY=1 vs wire anomaly:** There is an apparent contradiction: BUSY=1 on the slave requires SDA to fall (START detection), yet the wire test shows SDA (PB3) cannot follow PB7 going low. Possible explanations:
1. The wire has very high but not infinite resistance (~20–50 kΩ), allowing a partial SDA fall that triggers the I2C's START detector (analog hysteresis) but not clean bit sampling.
2. BUSY was set by a residual state from a previous partial transaction that SWRST did not fully clear.
3. The I2C start detector has a lower threshold than VIL for digital logic.

Either way, the SDA bit sampling during address transmission would be unreliable or incorrect with such a wire, explaining why ADDR is never set.

---

## 5. Conclusion

The evidence strongly points to a **hardware issue with the SDA jumper wire (PB7↔PB3)**:

- All software registers are correctly configured (verified in SRAM)
- The SCL wire (PB6↔PB10) is confirmed working
- The SDA wire (PB7↔PB3) fails the direct GPIO continuity test
- Both I2C1 and I2C2 slave peripherals fail identically — ruling out peripheral-specific bugs
- The ARLO condition in the role-swap master confirms bus-level signal integrity issues on SDA

The internal 40 kΩ pull-up (without external resistors) may exacerbate a marginal wire connection by providing insufficient pull-up current to overcome any contact resistance.

---

## 6. Recommended Next Steps

1. **Physical inspection:** Verify PB7 and PB3 jumper wire connections on the BlackPill board. Replace the wire and re-run.

2. **External pull-up resistors:** Add 4.7 kΩ pull-up resistors between VCC and each of PB6/PB7/PB10/PB3 (or between VCC and the SDA/SCL bus nodes). The internal 40 kΩ pull-up is above the I2C spec maximum of 10 kΩ for SM mode.

3. **Use PB9 for I2C2_SDA:** PB9 is also AF9 = I2C2_SDA on F411 and is not a JTAG pin. Wiring would be PB7↔PB9. This would confirm whether PB3-specific behavior (JTAG default state, pin damage) is a contributing factor.

4. **LA capture:** Connect LA probe (P0.3) to PB7 or PB3 to directly observe what is on the SDA line during I2C transactions. The test plan already has `signal_checks: []` so LA captures would need to be added.

5. **Re-test after hardware fix:** Once wiring is confirmed good, restore original firmware (main.c is in diagnostic state; revert to clean version with just the SWRST fix).

---

## 7. Firmware State

The firmware at `firmware/targets/stm32f411ceu6_i2c_loopback/` has been modified during debugging:
- Added SRAM diagnostic dumps (0x2000FC10, 0x2000FC20, 0x2000FC30)
- Added GPIO wire continuity test before I2C init
- Role-swap experiment: I2C2=master, I2C1=slave (last committed state)
- I2C speed set to 10 kHz (CCR=800)

Before resuming this test, the firmware should be cleaned up (restore original role assignment, remove diagnostic code, restore 100 kHz speed).

The test plan (`tests/plans/stm32f411ceu6_i2c_loopback.json`) and firmware directory are preserved as-is for future use.
