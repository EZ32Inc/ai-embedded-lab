# Bring-Up Process Recording Spec v0.1

## Purpose

Technical bring-up work routinely produces debugging insights, family-specific
hardware knowledge, and reusable rules — but these are only valuable if they are
captured in a structured form during execution, not reconstructed from memory
afterward.

This spec defines seven required outputs for any bring-up, validation, or
targeted debug task.  The STM32G431CBU6 eight-test bring-up is used throughout
as the concrete motivating example.

---

## Scope

Applies to:
- New board bring-up (first hardware validation)
- New peripheral test on a known board
- Debug session resolving a hardware or firmware failure
- Port of existing firmware to a new MCU family

---

## Required Outputs

### 1. Upfront Task Goal

Written before any code is written or any test is run.

**Content:**
- What board / MCU / peripheral is under test
- What "done" looks like (specific pass criterion, not "it works")
- What is being reused from prior work, and what is new

**STM32G431 example:**
> Target: STM32G431CBU6 on ESP32JTAG bench (192.168.2.62).
> Done = smoke_stm32g431 8/8 PASS, board promoted to verified in manifest.yaml.
> Reusing: F411/F401 firmware structure, AEL test plan schema, observe_map pattern.
> New: G4 GPIO bus (AHB2 not AHB1), G4 ADC register map, unknown effective clock.

---

### 2. Process-Recording Goal

Written alongside the task goal.  Names what knowledge must be captured,
not just what must pass.

**Content:**
- Which assumptions from prior work are being carried forward (and therefore
  are at risk of being wrong)
- Which family-specific differences are known vs. unknown
- What the debugging evidence format will be (LA edges, pass/fail signal, etc.)

**STM32G431 example:**
> Assumptions carried from F4: GPIO MODER/ODR layout, SPI CR1 bit positions,
> ADC single-conversion flow.
> Known G4 differences: AHB2 bus for GPIO, new ADC init sequence (DEEPPWD/ADVREGEN).
> Unknown: whether SPI CR2 or ADC clock config differ from F4.
> Debug surface: PA2 edge count via LA — 0 edges = peripheral self-test failing.

---

### 3. Structured Checkpoints During Execution

At each natural stage boundary (build, flash, first signal, per-peripheral), record
the actual outcome against the expected outcome.  Do not batch these at the end.

**Format per checkpoint:**
```
Stage: <name>
Expected: <what pass looks like>
Actual: <measured result>
Status: PASS / FAIL / UNEXPECTED
Action: <what was done as a result>
```

**STM32G431 example checkpoints:**

```
Stage: gpio_signature flash + verify
Expected: PA2 150-400Hz, PA3 75-200Hz, ratio ~2:1
Actual: edges=0 on all LA bits
Status: FAIL
Action: Ran probe firmware to determine correct P0 bit mapping;
        discovered PA2→P0.3 (not P0.0 as assumed).

Stage: gpio_signature after observe_map correction
Expected: edges visible on P0.3
Actual: PA2 ~250Hz, PA3 ~125Hz, ratio=2.0 ✓
Status: PASS

Stage: uart_loopback, capture, exti, gpio_loopback, pwm
Expected: PA2 edges in 30-70Hz window
Actual: edges=0 (PA2 stuck LOW) on all five
Status: FAIL — systematic
Action: Identified common root: phase_ms threshold ≥10 at actual 500Hz
        SysTick = 25Hz PA2, below 30Hz minimum. Changed to ≥5 → 50Hz.

Stage: spi verify
Expected: PA2 ~50Hz (spi_good toggling)
Actual: edges=0, high=0, low=65532
Status: FAIL

Stage: adc verify
Expected: PA2 ~50Hz (adc_good toggling)
Actual: edges=0, high=0, low=65532
Status: FAIL
```

---

### 4. Problem → Experiment → Evidence → Fix Trace

For each failure, a four-field record written at the time of resolution.

**Format:**
```
Problem:    <symptom as measured, not inferred>
Hypothesis: <proposed root cause>
Experiment: <what was changed or added to test the hypothesis>
Evidence:   <what the measurement showed after the change>
Fix:        <exact code/config change that resolved it>
```

**STM32G431 SPI:**
```
Problem:    PA2 edges=0, high=0, low=65532 — spi_good never set
Hypothesis: spi1_transfer() times out waiting for RXNE; G4 SPI FIFO
            default threshold is 16-bit (two bytes), not 8-bit
Experiment: Added CR2 with DS=0111 (8-bit) and FRXTH=1; moved SPE
            to a separate write after CR1+CR2 configured
Evidence:   PA2 edges=25, high≈32k — spi_good set on ~50% of phase cycles ✓
Fix:        SPI1_CR2 = (7u << 8) | (1u << 12);  // DS=8-bit, FRXTH=1
            SPI1_CR1 |= (1u << 6);               // SPE last
```

**STM32G431 ADC:**
```
Problem:    PA2 edges=0 — adc_good never set; EOC never asserts
Hypothesis: ADC has no clock: G4 default CKMODE=00 (async) requires
            ADC PLL which is not configured; F4 ADC always had clock
            from PCLK2 implicitly
Experiment: Set ADC12_CCR CKMODE=01 (sync HCLK/1) before ADVREGEN
Evidence:   PA2 edges=25, high≈32k ✓
Fix:        ADC12_CCR |= (1u << 16);  // CKMODE=01, before ADVREGEN
```

---

### 5. Final Postmortem

Written after all tests pass.  One document, under one page.

**Required sections:**
- Final result (pass count, board status)
- Root cause per failure (reference the traces from §4)
- Why these failures were family-specific (not just a coding error)
- What debugging evidence led to each fix
- What would have prevented each failure

**STM32G431 postmortem:** see `docs/specs/stm32g431_bringup_postmortem_v0_1.md`

---

### 6. Reusable Rule / Skill Candidate

For each fix that is likely to recur on a different board or MCU, write a
standalone rule in the following form.

**Format:**
```
Rule: <short imperative statement>
Scope: <which MCU families / peripherals this applies to>
Why it matters: <what breaks if ignored, with symptom>
How to apply: <concrete code or config action>
Source: <bring-up where this was discovered>
```

**STM32G431 rules:**

```
Rule: Set SPI CR2.FRXTH=1 before enabling SPE on any STM32 with SPI FIFO.
Scope: STM32G0, G4, WB, WL, H7 — any family with enhanced SPI IP.
Why: Default FRXTH=0 means RXNE asserts only after 2 bytes received.
     Single-byte transfers will always time out.
     Symptom: spi_transfer() returns 0, status pin stuck LOW.
How: SPI1_CR2 = (7u << 8) | (1u << 12);  // DS=8-bit, FRXTH=1
     Write SPE separately: SPI1_CR1 |= (1u << 6);
Source: STM32G431CBU6 bring-up, 2026-03-16
```

```
Rule: Set ADC12_CCR.CKMODE before ADVREGEN on STM32G4 (and any family
      with ADC async clock domain).
Scope: STM32G4, STM32H5, STM32U5 — families where ADC clock is
       not automatically derived from APB.
Why: CKMODE=00 (default) requires ADC PLL. Without it, ADSTART
     never produces a conversion and EOC never asserts.
     Symptom: adc_read() times out, status pin stuck LOW.
     Calibration (ADCAL) may appear to complete despite no clock.
How: ADC12_CCR |= (1u << 16);  // CKMODE=01: sync HCLK/1
     This line must appear before ADC1_CR |= (1u << 28) (ADVREGEN).
Source: STM32G431CBU6 bring-up, 2026-03-16
```

---

### 7. Reuse Note

A brief forward-looking entry noting what is now available for the next
bring-up of the same or a related board.

**Format:**  bullet list, one line each.

**STM32G431 reuse note:**
- `configs/boards/stm32g431cbu6.yaml` — verified observe_map (PA2→P0.3,
  PA3→P0.0, PA4→P0.2, PB3→P0.1, PA8→LED); safe to reuse directly
- `firmware/targets/stm32g431_*/` — eight bare-metal templates covering
  GPIO, UART, SPI, ADC, capture, EXTI, loopback, PWM; all G4-correct
- `packs/smoke_stm32g431.json` — rerun this pack unchanged for any
  new STM32G431CBU6 unit to confirm board health
- `tools/probe_p0_connections.py` — rerun with `--no-flash` if P0
  wiring is ever in doubt on a new bench setup
- SPI FRXTH rule and ADC CKMODE rule (§6) apply to all G4 variants
  (G431, G441, G471, G473, G474, G483, G484)
- If porting to another G4 part: re-verify effective SysTick rate
  (observed ~8MHz / 500Hz on this unit; root cause unresolved)

---

## Process Summary (Checklist)

```
[ ] 1. Task goal written before first tool call
[ ] 2. Process-recording goal written (assumptions listed, unknowns named)
[ ] 3. Checkpoint recorded at each stage boundary
[ ] 4. Problem→experiment→evidence→fix trace written per failure
[ ] 5. Postmortem written after final PASS
[ ] 6. Rule/skill candidate written per novel fix
[ ] 7. Reuse note written pointing at what the next person can skip
```

All seven are required.  §3–4 are written during execution.
§5–7 are written after final PASS, before the session ends.

---

## When an Output Can Be Brief

- If a stage has no failures, the checkpoint is one line: `Stage X: PASS`.
- If a fix is a direct copy of a known rule from §6, the trace is one line:
  `Applied FRXTH rule — PASS`.
- The postmortem can be omitted only if there were zero failures and the
  reuse note is non-empty.

---

*Motivated by STM32G431CBU6 bring-up, 2026-03-16.*
*SPI (FRXTH) and ADC (CKMODE) failures were both preventable via G4-specific
source references, but were not caught because the process-recording path
was not enforced upfront.*
