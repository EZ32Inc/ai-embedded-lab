# STM32G4 Peripheral Init Rules

Two rules discovered during STM32G431CBU6 bring-up (2026-03-16).
Apply to any STM32 family using the enhanced SPI IP or the G4-style ADC.

---

## Rule 1 — SPI: Set FRXTH=1 before enabling SPE

**Scope:** STM32G0, G4, WB, WL, H7 (any family with enhanced SPI / FIFO)

**Symptom if missed:** `spi_transfer()` always times out; RXNE never asserts
for single-byte transfers; status pin stuck LOW; `edges=0` on LA.

**Why:** The enhanced SPI has a 32-bit FIFO. `CR2.FRXTH` controls the RXNE
threshold:
- `FRXTH=0` (default): RXNE asserts when FIFO ≥ 16 bits (two bytes received)
- `FRXTH=1`: RXNE asserts when FIFO ≥ 8 bits (one byte received)

For 8-bit transfers, `FRXTH=0` means RXNE never asserts. This register does
not exist on STM32F1/F4, so code ported from those families silently breaks.

**Fix:**
```c
/* Configure CR1 and CR2 before SPE */
SPI1_CR1 = (1u << 2) |   /* MSTR */
           (7u << 3) |   /* BR = fPCLK/256 */
           (1u << 8) |   /* SSI */
           (1u << 9);    /* SSM */
SPI1_CR2 = (7u << 8) |  /* DS = 0111 (8-bit data size) */
           (1u << 12);   /* FRXTH = 1 (8-bit RXNE threshold) */
SPI1_CR1 |= (1u << 6);  /* SPE — enable last */
```

**Detection:** If migrating SPI code from F1/F4 to G4, search for any
`CR1` write that includes `SPE` simultaneously with config bits and has
no corresponding `CR2` write. That pattern is always wrong on G4 for
8-bit transfers.

---

## Rule 2 — ADC: Set CKMODE before ADVREGEN

**Scope:** STM32G4, STM32H5, STM32U5 (families with ADC async clock domain)

**Symptom if missed:** `ADSTART` never produces a conversion; `EOC` never
asserts; `adc_read()` times out; status pin stuck LOW; `edges=0` on LA.
Calibration (`ADCAL`) may appear to complete even without a clock.

**Why:** STM32G4 ADC has an independent clock domain controlled by
`ADC12_CCR.CKMODE[1:0]`:
- `CKMODE=00` (default): asynchronous clock from `PLLADC1CLK` — requires
  the ADC PLL to be configured and running
- `CKMODE=01`: synchronous `HCLK/1` — works with no additional clock setup

On STM32F4, the ADC clock is always derived from APB2 via a prescaler;
there is no concept of "no clock." Code written with this mental model
omits CKMODE and fails silently on G4.

**Fix:**
```c
/* ADC12 common register base: 0x50000300, CCR at offset 0x08 */
#define ADC12_CCR  (*(volatile uint32_t *)0x50000308u)

static void adc1_init(void)
{
    /* Must be set before ADVREGEN (before powering on the ADC) */
    ADC12_CCR |= (1u << 16);   /* CKMODE=01: synchronous HCLK/1 */

    ADC1_CR &= ~(1u << 29);    /* clear DEEPPWD */
    ADC1_CR |=  (1u << 28);    /* set ADVREGEN */
    /* ... regulator wait, calibration, ADEN, ADRDY ... */
}
```

**Detection:** Any G4 ADC init that omits a write to `ADC12_CCR` before
`ADVREGEN` is likely broken unless an ADC PLL has been explicitly configured.

---

## Reference

- ST LL driver constants (from STM32CubeG4):
  - `LL_SPI_RX_FIFO_TH_QUARTER` = `SPI_CR2_FRXTH` (bit 12)
  - `LL_ADC_CLOCK_SYNC_PCLK_DIV1` = `ADC_CCR_CKMODE_0` (bit 16)
- Confirmed via CubeMX LL header:
  `/home/aes/work/stm32g431cbu6_gpio/Drivers/STM32G4xx_HAL_Driver/Inc/`
  - `stm32g4xx_ll_spi.h` line 282: `LL_SPI_RX_FIFO_TH_QUARTER`
  - `stm32g4xx_ll_adc.h` line 745: `LL_ADC_CLOCK_SYNC_PCLK_DIV1`
- Evidence: diff of F401 vs G431 firmware shows CR2 absent in original
  G431 SPI; ADC init rewritten for G4 but CKMODE step omitted due to F4
  mental model (F4 ADC clock is implicit from APB2).
