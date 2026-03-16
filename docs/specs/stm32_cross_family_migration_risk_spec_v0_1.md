# Cross-Family MCU Migration Risk Spec v0.1

> **Scope note:** The two error patterns defined here — *missing transplant*
> and *implicit assumption* — are general. They apply to any MCU family
> migration (nRF52→nRF54, RP2040→RP2350, ESP32→ESP32-S3, etc.). This
> document uses STM32 as the concrete example because that is where the
> patterns were first identified and confirmed on hardware.

---

## Background

During STM32G431CBU6 bring-up, two tests in `smoke_stm32g431` failed on first
run: `stm32g431_spi` and `stm32g431_adc`. Both were fixed and the pack reached
8/8 PASS. The board was promoted to verified.

The debugging process revealed a root cause pattern that is not specific to
this board: **peripheral bring-up for a new MCU family cannot default to
direct migration from an older family's bare-metal code.**

---

## Two Error Patterns

### Pattern 1 — Missing Transplant

The new-family code is structurally a copy of the old-family code. A mechanism
required by the new family does not exist in the old code at all, so it is
never implemented — and never noticed during the port.

**Detection question:** Is the new-family code line-for-line similar to the
old-family code, with changes limited to header, register names, instance
number, and pin numbers — but no new registers or init steps added?

### Pattern 2 — Implicit Assumption from Prior Family

The new-family code is not a mechanical copy; it was written from scratch.
However, the implementer carried over a default expectation from the prior
family — for example, that a clock is always available, or that a status flag
behaves the same way. A required initialization step is omitted because the
prior-family model made it invisible.

**Detection question:** Does the new code omit a step that the target family's
CubeMX LL output includes — specifically a clock source selection, power
domain enable, or calibration step that the prior family handled implicitly?

---

## STM32G431 Evidence

### A. SPI — Missing Transplant

**Symptom:** `stm32g431_spi` fails. PA2 has zero edges (LA: `edges=0, high=0,
low=65532`). `spi_good` is never set. `spi1_transfer()` always times out.

**Root cause:** The G431 SPI firmware was ported from an F401-style
implementation. The port replaced the header, register names, SPI instance,
and pin numbers — nothing else. The STM32G4 SPI peripheral has a 32-bit FIFO
and a `CR2.FRXTH` bit that controls the RXNE assertion threshold:

| `FRXTH` | RXNE asserts when FIFO holds |
|---------|------------------------------|
| 0 (default) | ≥ 16 bits (two bytes) |
| 1 | ≥ 8 bits (one byte) |

For single-byte transfers, `FRXTH=0` means RXNE never asserts. The F4 SPI has
no FIFO and no `FRXTH` bit, so the concept was entirely absent from the source
code. A direct code diff of `stm32f401_spi/main.c` vs. `stm32g431_spi/main.c`
confirms the G431 version had no `CR2` write at all in the original.

**Fix:**
```c
SPI1_CR2 = (7u << 8) | (1u << 12);  /* DS=8-bit, FRXTH=1 */
SPI1_CR1 |= (1u << 6);              /* SPE — set after CR1+CR2 configured */
```

**Why it is a missing transplant:** The F401 source contained no CR2 write,
no FRXTH concept. The port faithfully reproduced everything that existed and
could not reproduce what did not.

---

### B. ADC — Implicit Assumption from Prior Family

**Symptom:** `stm32g431_adc` fails. PA2 has zero edges. `adc_good` is never
set. `EOC` never asserts despite `ADSTART` being written.

**Root cause:** The G431 ADC firmware was written from scratch for the G4
register map, not copied from F4. It correctly includes all G4-specific
initialization steps: `DEEPPWD`, `ADVREGEN`, `ADCAL`, `ADEN`. However,
`ADC12_CCR.CKMODE` was not set.

On STM32G4, `CKMODE[1:0]` selects the ADC clock source:

| `CKMODE` | Clock source |
|----------|-------------|
| `00` (default) | Asynchronous — requires `PLLADC1CLK` (ADC PLL) |
| `01` | Synchronous `HCLK/1` — no PLL required |

The ADC PLL was not configured, so the ADC had no clock. Calibration (`ADCAL`)
appeared to complete (the bit cleared), but `ADSTART` produced nothing.

On STM32F4, the ADC clock is always derived from APB2 via a prescaler in
`ADC_CCR.ADCPRE`. There is no concept of "no ADC clock." Code written by
someone familiar with F4 ADC naturally skips the clock source selection step,
because on F4 that step does not exist — the clock is always present.

**Fix:**
```c
/* Must precede ADC1_CR |= ADVREGEN */
ADC12_CCR |= (1u << 16);  /* CKMODE=01: synchronous HCLK/1 */
```

**Why it is an implicit assumption:** The code was written fresh using G4
documentation. CKMODE was not overlooked because of mechanical copy; it was
overlooked because the F4 mental model made a dedicated clock-source step
feel unnecessary.

---

## Open Item: Effective Clock on This G431 Unit

During bring-up, the effective SysTick rate measured at ~500 Hz with RVR=15999,
implying an MCU clock of approximately 8 MHz — not the expected HSI 16 MHz.
Root cause is unresolved. An attempt to add explicit HSI clock init regressed
the frequencies further, so it was reverted.

**Impact on future work:** Any bare-metal firmware reused from this bring-up
assumes a ~500 Hz SysTick (not 1 kHz). Do not assume 16 MHz HSI on this unit
without first measuring. This should be investigated on the next session with
this board.

---

## Why SPI and ADC Are High-Risk Peripherals

The following peripherals are most likely to break silently across family
migrations:

- **SPI** — FIFO thresholds, DR access width, SPE sequencing
- **ADC** — clock source, power-up sequence, calibration, common registers
- **UART** — FIFO control, oversampling, baud rate register encoding
- **TIM** — capture/compare differences, ARR buffering behaviour
- **EXTI, capture, PWM** — trigger source semantics, DMA interactions

GPIO output/toggle code tends to survive family migration because the
MODER/ODR layout is stable across STM32 families. The peripherals above fail
silently and are hard to diagnose without a hardware-observable status signal
(such as a dedicated output pin monitored by LA).

---

## Code Review Checklist

Answer each question yes/no. A "yes" is a flag requiring verification against
the target family's CubeMX LL output before the code is accepted.

**For ported code (Missing Transplant screen):**

1. Are the only changes header, register names, instance number, and pins?
2. Does the target family's peripheral have a FIFO, threshold register, or
   common control register absent from the source family?
3. Does the target family's LL init call any function (e.g.,
   `LL_SPI_SetRxFIFOThreshold`, `LL_ADC_SetCommonClock`) that has no
   counterpart in the ported code?

**For newly written code (Implicit Assumption screen):**

1. Does the code omit a clock source selection that the target family requires
   but the prior family provided automatically?
2. Does the code omit an explicit power-on or voltage regulator enable step?
3. Does the target family's CubeMX LL output include an `MX_XXX_Init()` call
   or sub-call absent from this code?

---

## Mandatory Rule: Initialization Reference Priority

For any peripheral bring-up on a new MCU family — especially SPI, ADC, UART,
TIM, EXTI, capture, PWM — **the primary initialization reference must come
from a target-family-native source**:

| Priority | Source |
|----------|--------|
| 1 | CubeMX LL-mode generated init (`MX_XXX_Init()`) for the exact MCU |
| 2 | Official vendor SDK example for the exact family (`STM32CubeG4`, etc.) |
| 3 | Verified bare-metal code from the same family or sub-series in this repo |
| 4 (last resort) | Code from a different family — structural reference only, not an authority on register values or init sequence |

---

## Recommended Workflow

1. Open CubeMX, select the exact target MCU
2. Enable the peripheral under test; select **LL driver** generation mode
3. Generate the project and open `MX_XXX_Init()`
4. Identify any calls absent from the existing bare-metal template:
   - Clock source selections (`LL_ADC_SetCommonClock`, etc.)
   - FIFO / threshold settings (`LL_SPI_SetRxFIFOThreshold`, etc.)
   - Enable sequencing constraints (SPE last, ADVREGEN before ADCAL, etc.)
5. Map those steps to register writes in the AEL bare-metal firmware
6. Run smoke tests
7. On failure, check before touching application logic:
   - Family-specific flag semantics (RXNE threshold, EOC conditions)
   - Family-specific clock source (ADC, USB, RNG common clock registers)
   - Enable / calibration / ready sequence
   - FIFO / threshold / common register configuration

---

## STM32 LL Constant Cross-Reference

Key LL constants that encode family-specific requirements. If the bare-metal
firmware has no equivalent register write, the init is likely incomplete.

| LL Constant | Register bit | Meaning | Affected STM32 families |
|---|---|---|---|
| `LL_SPI_RX_FIFO_TH_QUARTER` | `SPI_CR2_FRXTH` (bit 12) | Set RXNE threshold to 8-bit; required for single-byte transfers | G0, G4, WB, WL, H7 |
| `LL_ADC_CLOCK_SYNC_PCLK_DIV1` | `ADC_CCR_CKMODE_0` (bit 16) | Sync ADC clock HCLK/1; use when no ADC PLL is configured | G4, H5, U5 |

Verified against STM32CubeG4 LL headers (local copy):
- `stm32g4xx_ll_spi.h` line 282 — `LL_SPI_RX_FIFO_TH_QUARTER`
- `stm32g4xx_ll_adc.h` line 745 — `LL_ADC_CLOCK_SYNC_PCLK_DIV1`

---

## Related Documents

- `docs/specs/bringup_process_recording_spec_v0_1.md` — required outputs
  and checkpoints for any bring-up session
- `docs/skills/stm32g4_peripheral_init_rules.md` — G4-specific quick
  reference: SPI FRXTH rule, ADC CKMODE rule, with code snippets

---

## Summary

> When bringing up a peripheral on a new MCU family, do not default to
> migrating from another family's bare-metal code. Use the target family's
> CubeMX LL output or official SDK example as the initialization authority.
> This prevents two failure classes: *missing transplant* (a required
> mechanism that did not exist in the source) and *implicit assumption* (a
> default that held on the source family but not the target). Both produce
> silent peripheral failures that are hard to diagnose without a
> hardware-observable status signal.

*Source: STM32G431CBU6 bring-up, 2026-03-16.
SPI FRXTH and ADC CKMODE failures confirmed via LA evidence and F401↔G431
code diff.*
