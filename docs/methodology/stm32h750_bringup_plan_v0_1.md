# Plan: STM32H750 Bring-Up — Pre-Execution Rehearsal

## Status
Pre-execution plan — not yet started. Written as a rehearsal before any code is generated.
Review comments incorporated (2026-03-16): mailbox address treated as provisional;
Step 0 scoped to minimal truth only; startup reuse policy clarified; peripheral gate strengthened.

---

## Purpose

This document describes exactly how I would approach the STM32H750 bring-up —
especially how I would generate firmware code — before any work begins.

The user's key question is: **"你将如何生成代码？"**

This is the right question to ask. The STM32G431 experience taught us that
code generation strategy is where the most dangerous hidden failures live.
This document answers that question honestly, step by step.

---

## 1. Why Code Generation Strategy Matters Here

The STM32H750 is not "a faster G431." It is a fundamentally different device:

| Dimension | STM32G431 (known) | STM32H750 (new) |
|---|---|---|
| Core | Cortex-M4 | Cortex-M7 |
| Clock default | 16 MHz HSI | 64 MHz HSI |
| GPIO bus | AHB2 | AHB4 |
| SRAM layout | single region, simple | 6 separate regions on different buses |
| D-cache | none | present — affects mailbox reads |
| Flash size | 128 KB | 128 KB (H750VBT6) |
| Flash latency | simple | must be set before increasing clock |
| ADC clock | CKMODE required | different clock topology again |
| Debugger SRAM access | all SRAM via AHB | DTCM NOT accessible via AHB |

If I copy G431 firmware and change register addresses, I will reproduce
exactly the same class of errors we found with SPI and ADC —
but now with more vectors, because the H750 has more family-specific mechanisms.

**The rule from `stm32_cross_family_migration_risk_spec_v0_1.md` applies in full.**

---

## 2. What I Will NOT Do

- I will not copy `firmware/targets/stm32g431*/main.c` and change addresses
- I will not assume the GPIO clock enable register has the same offset as G431
- I will not assume the SysTick effective clock is the same
- I will not assume the SRAM layout is safe for mailbox placement without checking
- I will not assume caches are disabled by default (they are, but I will verify)
- I will not start writing peripheral firmware before Step 0 passes

---

## 3. The Critical H750-Specific Risk: D-Cache and the Mailbox

This is the most dangerous H750-specific issue, and it does not exist on G431 at all.

The Cortex-M7 has a D-cache. When the debugger reads a memory address via SWD,
it goes through the AHB bus — but the CPU writes through the D-cache first.
If the cache line containing the mailbox is not flushed, GDB will read **stale data**:
the mailbox might say `status=RUNNING` even though the firmware wrote `STATUS_PASS`.

**This would cause `check.mailbox_verify` to report FAIL on a board that is actually
passing — a silent false negative that is very hard to diagnose.**

### My approach

For `minimal_runtime_mailbox` on H750:

1. **Do not enable D-cache** in the minimal firmware. The H750 does not enable
   caches in hardware reset; they must be explicitly enabled via SCB->CCR.
   The minimal firmware will not touch the cache registers.
   This means cache is off, and the mailbox write is coherent for the debugger.

2. **Mailbox address**: use SRAM1 (0x30000000) or SRAM4 (0x38000000),
   not DTCM (0x20000000). DTCM is directly coupled to the M7 core and is
   **NOT accessible via the AHB bus** — the debugger cannot read it.
   GDB would always read zeros from a DTCM mailbox address.

3. Confirm the chosen address is writable by firmware and readable by GDB
   before integrating into the pipeline.

**Mailbox address is provisional until verified.** Candidates are SRAM1 end
(`0x30007F00`) or SRAM4 start + offset (`0x38000F00`), but neither is fixed.
The verification sequence before finalizing the address is:

```
1. Confirm SRAM region is AHB-accessible (not DTCM)
2. Build firmware and run arm-none-eabi-nm — confirm .bss does not reach the candidate
3. Flash minimal firmware, write a known pattern to the address from firmware
4. Read it back with GDB: x/4xw <candidate_addr>
5. Confirm GDB sees the same value firmware wrote
6. Only then set this address as AEL_MAILBOX_ADDR
```

Do not add the address to the test plan or pipeline configuration until step 5 passes.

---

## 4. Code Generation Strategy

### 4.1 Source Rule

Every register address and initialization sequence for H750 will be derived from:

1. **STM32H750 Reference Manual (RM0433)** — the authoritative source
2. **STM32H750 datasheet** — for pin alternate functions, SRAM layout
3. **STM32CubeMX H750 output** — as a cross-check, not as the primary source

I will **not** derive H750 code from G431 or F411 implementations.
Structural patterns (mailbox struct, startup boilerplate, SysTick polling loop)
are reusable. Register addresses, bit positions, and initialization sequences
are not — they must come from RM0433.

### 4.2 What I Will Look Up Before Writing Any Line of Code

Before writing `main.c` for `minimal_runtime_mailbox`, I will confirm from RM0433:

**SRAM layout**
- DTCM: 0x20000000, 128 KB — M7-only, not AHB accessible → NOT usable for mailbox
- AXI SRAM: 0x24000000, 512 KB — AHB accessible, cacheable
- SRAM1: 0x30000000, 128 KB — AHB accessible, not in default cacheable region
- SRAM4: 0x38000000, 64 KB — AHB accessible, used by D3 domain
- → Mailbox provisional candidate: `SRAM1 end - 256 bytes = 0x30007F00`
  — subject to firmware .bss check and GDB read-back verification before finalizing

**RCC for GPIO**
- H750 uses `RCC_AHB4ENR` for GPIO clocks (not AHB2ENR like G431)
- GPIOA clock: `RCC_AHB4ENR |= (1u << 0)`
- Confirm register address: RM0433 §8.7.37

**GPIO register base addresses**
- GPIOA base: 0x58020000 (H750, AHB4 domain)
  — completely different from G431's 0x48000000
- MODER, ODR offsets are the same (0x00, 0x14) — Cortex-M GPIO standard layout
- Must use H750-specific base address

**SysTick**
- SysTick is Cortex-M7 standard (0xE000E010) — same address, same registers
- But: SysTick CLKSOURCE=1 uses processor clock
- H750 default processor clock after reset = 64 MHz HSI
- With RVR=63999: tick rate = 64 MHz / 64000 = **1000 Hz** (1 ms per tick)
- This is different from G431's ~500 Hz — delay values will need adjustment

**Flash latency (for future peripheral tests, not minimal)**
- H750 at 64 MHz requires FLASH_ACR.LATENCY ≥ 2 wait states
- For minimal firmware running at 64 MHz HSI (no PLL), LATENCY=1 is correct
- This must be set before any clock switch — important for future tests

**Linker script**
- Stack top: end of DTCM = 0x20020000 (DTCM is 128 KB, starts at 0x20000000)
- Code in flash: starts at 0x08000000
- `.data` and `.bss` in AXI SRAM: 0x24000000
- New linker script needed — cannot reuse G431's `stm32g431.ld`

### 4.3 File Generation Order

```
1. stm32h750.ld         — new linker script, derived from H750 memory map
2. startup.c            — Reset_Handler, vector table
3. main.c               — minimal_runtime_mailbox only
4. Makefile             — -mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard
```

**Startup.c reuse policy:** The *structure* of `startup.c` (Reset_Handler
copy-.data, zero-.bss, call main, Default_Handler) is reusable from G431.
The following must NOT be inherited:
- vector table size and entries (H750 has ~150 interrupts vs G431's ~101)
- any memory region symbols (_sdata, _estack, etc.) — must match H750 linker script
- any assumption about stack or SRAM layout

Treat it as: "same C pattern, completely new memory map."

Peripheral firmwares (UART, SPI, ADC, etc.) will only be written after
`minimal_runtime_mailbox` passes on hardware. This is a hard gate.

### 4.4 Makefile Flags

The G431 used `-mcpu=cortex-m4`. The H750 requires:

```makefile
CFLAGS = -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard \
         -O2 -ffreestanding -fdata-sections -ffunction-sections \
         -Wall -Wextra -nostdlib
```

Wrong core flag would produce code that might silently misbehave (wrong
instruction scheduling, wrong FPU usage).

---

## 5. Bring-Up Execution Plan (following `new_board_bringup_sequence_v0_1.md`)

### Step 0 — minimal_runtime_mailbox

The goal of Step 0 is **minimal runtime truth**, not full H7 initialization.
It must answer one question: can the MCU be flashed, booted, and read over SWD?
Nothing else.

**What Step 0 does:**
- Enable one GPIO clock (RCC_AHB4ENR)
- Configure PA8 as output (LED, visual only)
- Start SysTick for delay (processor clock, no PLL)
- Write mailbox: magic + STATUS_RUNNING, run self-check, write STATUS_PASS or FAIL
- Spin, incrementing detail0

**What Step 0 explicitly does NOT do:**
- Does not enable D-cache or I-cache (leave SCB->CCR untouched)
- Does not configure PLL or change the clock source from HSI
- Does not set flash latency beyond what 64 MHz HSI requires
- Does not initialize any peripheral (no UART, SPI, ADC, TIM)
- Does not configure MPU
- Does not initialize FPU (minimal firmware avoids floating point)

**Before writing code:**
1. Confirm H750 variant (VBT6 = 100-pin, 128 KB flash, 1 MB RAM)
2. Verify mailbox address candidate per the provisional address procedure (§3)
3. Confirm GDB can attach: `target extended-remote ip:4242` → `monitor a` → `attach 1`

**Code generation:**
- Write `stm32h750.ld` from RM0433 memory map — new file, no reuse
- Write `startup.c` — reuse Reset_Handler structure, new vector table and symbols
- Write `main.c` — GPIO + SysTick from RM0433, mailbox address provisional

**Acceptance gate (Step 0 is not complete until all four pass):**
```
✓ GDB attaches without error
✓ python3 tools/read_mailbox.py --ip <ip> --addr <provisional_addr>
      → magic=0xAE100001
      → status=2 (PASS)
      → detail0 increases between two reads separated by ~1s
✓ Verified in isolation — no other firmware running
```

**Do not proceed to Step 1 until all four acceptance criteria pass.**

### Step 1 — Wiring / Observe-Map Verification

Same Method B (frequency-coded parallel scan) as G431.
Firmware drives multiple GPIOs at distinct frequencies.
LA captures and infers wiring mapping.

H750-specific: confirm which PA2/PA3/PA8 alternate function pins exist
on the specific H750 package (VBT6 = 100-pin LQFP).

### Step 2 — Pair-Level GPIO Sanity

Drive each pin individually, verify LA sees the level.
Confirm no GPIO clock issues (AHB4ENR, not AHB2ENR — this is a likely
missing-transplant candidate for any code derived from G431).

### Step 3 — Full Peripheral Tests

**Hard gate.** Peripheral work begins only after ALL of the following are confirmed:

```
✓ Step 0: flash OK, boot OK, mailbox write OK, mailbox read via GDB OK
✓ Step 1: wiring map confirmed in observe_map, LA captures expected signals
✓ Step 2: each GPIO pin independently drivable and readable
```

If any of the above fails, the failure must be resolved before proceeding.
Do not attempt peripheral tests to "see if maybe it works anyway."

Then derive peripheral firmwares from RM0433:
- UART: check USART clock source (H750 has per-USART clock mux in RCC)
- SPI: check FIFO behavior (H750 SPI is also FIFO-based, like G431 — FRXTH equivalent)
- ADC: check ADC clock source (H750 has ADC_CCR.CKMODE, similar issue to G431)
- TIM: check timer clock domains (APB1 vs APB2 multipliers)
- EXTI: check EXTICR register location (SYSCFG on H750 is in APB4 domain)

Each peripheral will be cross-checked against RM0433 before code is written.

---

## 6. Known Risks and How I Will Handle Them

| Risk | Likely consequence | Mitigation |
|---|---|---|
| D-cache on mailbox address | `check.mailbox_verify` reads stale data | Don't enable D-cache; use SRAM1 not DTCM |
| Wrong mailbox address (DTCM) | GDB reads zeros permanently | Use SRAM1/SRAM4 (AHB-accessible); verify with GDB read-back before finalizing |
| GPIO base address from G431 | GPIO never responds | Derive from RM0433 §8; H750 GPIOA = 0x58020000 |
| Wrong AHB bus for GPIO clock | GPIO works but clock enable silently fails | Use RCC_AHB4ENR, not AHB2ENR |
| Wrong -mcpu flag | Code assembles but may crash silently | Use cortex-m7 explicitly in Makefile |
| SysTick delay values wrong | Timing off (but functional) | Recalibrate: 64 MHz / 64000 = 1 kHz |
| ADC clock not configured | ADC EOC never fires (same as G431) | Check H750 ADC_CCR.CKMODE before writing ADC code |
| UART clock mux not set | UART baud wrong or no clock | Check per-UART clock source in RCC_D2CCIP2R |

---

## 7. Five-Part Task Declaration (per `task_five_part_closure_rule_v0_1.md`)

**Technical goal:** complete STM32H750 bring-up through minimal_runtime_mailbox
PASS, then wiring map, then full smoke pack.

**Process goals to record:**
- Any H750-specific register differences discovered during coding
- Any failures in minimal_runtime_mailbox and their root causes
- Any D-cache or SRAM bus access surprises

**Asset goals:**
- `stm32h750_peripheral_init_rules.md` — H750-specific init rules
- Updated `ael_mailbox_contract_v0_1.md` if new SRAM address strategy is needed
- New `stm32h750_cross_family_risk_notes.md` if H7-specific patterns emerge

**Five-part closure expected outputs:**
1. Task summary: H750 smoke pack result and verified status
2. Key failures and fixes: any family-specific init failures
3. New rules: H750-specific rules (cache, clock, SRAM access)
4. Skills / workflow: updated mailbox contract for H7 family
5. Next defaults: what to do first on any future H7 board

---

## 8. What Success Looks Like

**Milestone A (Step 0):** `read_mailbox.py` returns `status=PASS` on H750.
This confirms: flash works, MCU boots, SRAM1 is writable, SWD readable.

**Milestone B (Steps 1–2):** wiring map confirmed, GPIO sanity passes.

**Milestone C (Step 3):** `smoke_stm32h750` pack runs and passes.

**Milestone D (Generalization test):** the fact that we followed the documented
method on a new family and it worked confirms the method is portable —
not just a G431-specific artifact.

---

## One-Sentence Summary

For STM32H750, every register address and initialization sequence will be
derived from RM0433 (not from G431), the mailbox will be placed in SRAM1
(AHB-accessible, not DTCM), D-cache will not be enabled in minimal firmware,
and no peripheral test will be attempted until `minimal_runtime_mailbox` passes
on hardware — following the four-step bring-up sequence exactly as documented.
