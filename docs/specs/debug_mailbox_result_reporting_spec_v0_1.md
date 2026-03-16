# Memo: Debug Mailbox in Target RAM for AEL Test Result Reporting v0.1

## Status
Draft — for decision on whether to proceed with a proof-of-concept experiment

---

## Table of Contents

1. [Background](#1-background)
2. [Core Idea](#2-core-idea)
3. [Why This Is Valuable](#3-why-this-is-valuable)
4. [Proposed First Version](#4-proposed-first-version)
5. [Recommended Minimal Experiment](#5-recommended-minimal-experiment)
6. [Mailbox Evolution Path](#6-mailbox-evolution-path)
7. [Design Choices](#7-design-choices)
8. [Relationship to Existing GPIO Result Signaling](#8-relationship-to-existing-gpio-result-signaling)
9. [Risks and Unknowns](#9-risks-and-unknowns)
10. [Recommended Next Step](#10-recommended-next-step)
11. [Decision Framing](#11-decision-framing)

---

## 1. Background

In the current style of DUT testing, the standard reporting pattern is:

- DUT runs a test
- DUT indicates pass/fail through GPIO behavior (toggling, frequency, high/low)
- ESP32JTAG observes that signal via the logic analyzer
- AEL interprets the result

This works, but it has limitations:

- it depends on extra signal wiring
- the reporting path itself can be miswired
- it only carries limited information (essentially one bit per observable)
- it is awkward for detailed debug status or error codes
- it adds dependence on external observation channels even when SWD/JTAG is
  already present and active

During recent work on the STM32G431 bring-up, time was lost because wiring
mismatches caused the result GPIO to be observed on the wrong channel. This
highlighted that the GPIO result path adds a layer of fragility that could be
avoided if the debug link itself were used as the result path.

**The alternative:** let the DUT write structured status into RAM, and let
ESP32JTAG read that RAM over the already-present SWD/JTAG connection.

---

## 2. Core Idea

Define a fixed RAM location — either by absolute address or by linker symbol —
as a **test mailbox**.

The DUT test firmware writes structured state into that mailbox as it runs.
ESP32JTAG attaches, reads the mailbox through SWD/JTAG, and reports the result
back to AEL.

Instead of:
> "toggle a GPIO to indicate success"

we move to:
> "write status and error details into RAM; the debug link reads them"

The debug connection that already exists for flashing and attaching becomes the
result reporting channel as well.

---

## 3. Why This Is Valuable

### 3.1 Removes dependence on a result GPIO

A result GPIO still depends on correct wiring, correct channel mapping, correct
external observation, and sufficient instrument interpretation. Any of these can
go wrong silently. A RAM mailbox removes that dependency entirely for the result
path — the SWD/JTAG connection is already required for flashing, so no
additional wiring is needed.

### 3.2 Carries richer information than a GPIO

A GPIO signal usually encodes at most a few bits. A mailbox can carry:

- current status (running / pass / fail)
- current phase or step
- error code
- measured value
- expected value
- internal debug state
- timeout counts

This makes failures actionable rather than just observable.

### 3.3 Better for automation

AEL aims to run a full AI-controlled validation loop. A mailbox is better
suited for automation because it is machine-readable, structured, extensible,
and easy to log and post-process without interpretation.

### 3.4 Better for process capture

A mailbox naturally supports stage reporting, failure localization, and
reproducible result capture. This aligns with the broader AEL goal of recording
not only outcomes but also process and evidence, as defined in
`docs/specs/bringup_process_recording_spec_v0_1.md`.

### 3.5 Natural fit for ESP32JTAG

ESP32JTAG already exists to interact with the DUT through debug access.
Reading target memory is a minimal extension of that existing role. No new
hardware or wiring is required.

---

## 4. Proposed First Version

The first version should be intentionally minimal.

### 4.1 DUT-Side Mailbox Structure

```c
#define MAILBOX_MAGIC  0xAE100001u

#define STATUS_EMPTY   0u
#define STATUS_RUNNING 1u
#define STATUS_PASS    2u
#define STATUS_FAIL    3u

struct test_mailbox {
    uint32_t magic;       /* always MAILBOX_MAGIC when valid */
    uint32_t status;      /* STATUS_xxx value */
    uint32_t error_code;  /* 0 = none; non-zero = test-specific failure code */
    uint32_t detail0;     /* test-specific diagnostic field; 0 if unused */
};
```

The magic value (`0xAE100001`) serves two purposes: it confirms the mailbox
has been written by the expected firmware, and it distinguishes a valid
mailbox from uninitialized RAM (which would read as `0x00000000` or
`0xFFFFFFFF` depending on reset state).

### 4.2 DUT Firmware Behavior

**At test start:**
```c
mailbox.magic      = MAILBOX_MAGIC;
mailbox.status     = STATUS_RUNNING;
mailbox.error_code = 0u;
mailbox.detail0    = 0u;
```

**On success:**
```c
mailbox.status = STATUS_PASS;
```

**On failure:**
```c
mailbox.error_code = <specific_error>;
mailbox.detail0    = <relevant_context>;  /* optional */
mailbox.status     = STATUS_FAIL;         /* write status last */
```

Status must be written **last** so that a partial write is never mistaken for
a complete result. After writing the final status, the DUT should enter an
infinite loop to allow reliable readout.

### 4.3 Mailbox Placement

**For the first experiment:** place the mailbox at a fixed absolute address
near the start of SRAM. For STM32G431 (SRAM1 base 0x20000000):

```c
#define MAILBOX_ADDR  0x20000000u
volatile struct test_mailbox * const mailbox =
    (volatile struct test_mailbox *)MAILBOX_ADDR;
```

The struct occupies 16 bytes. This address is well within SRAM and avoids
the stack region (which grows from the top of SRAM).

**For production use:** define a linker-reserved mailbox region (see
Section 7.1).

### 4.4 ESP32JTAG First-Version Support

Add only the minimum support needed:

1. attach to and halt the target
2. read 16 bytes from the mailbox address
3. parse the mailbox struct
4. return structured mailbox content to AEL

AEL receives the result as a structured object (magic, status, error_code,
detail0) rather than a pass/fail signal derived from GPIO observation.

---

## 5. Recommended Minimal Experiment

### Goal

Prove that the end-to-end mailbox path works reliably on one board before
investing in generalization.

**Recommended first board: STM32G431CBU6.** SWD is already working, the board
is verified, and the AEL flash pipeline is proven. This eliminates all
infrastructure unknowns and isolates the mailbox read as the only new variable.

### Test Firmware

A simple DUT firmware that:

1. writes `magic = MAILBOX_MAGIC`, `status = STATUS_RUNNING`
2. waits ~100 ms
3. writes `status = STATUS_PASS`
4. enters an infinite loop

Then a failure variant that:

1. writes `magic = MAILBOX_MAGIC`, `status = STATUS_RUNNING`
2. waits ~100 ms
3. writes `error_code = 0xDEAD0001`, `status = STATUS_FAIL`
4. enters an infinite loop

### Success Criteria

| Check | Expected |
|-------|----------|
| Magic read | `0xAE100001` |
| Status in pass variant | `2` (STATUS_PASS) |
| Status in fail variant | `3` (STATUS_FAIL) |
| Error code in fail variant | `0xDEAD0001` |
| Result independent of GPIO wiring | confirmed — no GPIO signal used |
| Reliable across 3 consecutive reads | no variation observed |

If all criteria pass, the concept is validated and the evolution path can
begin.

---

## 6. Mailbox Evolution Path

### Stage 1 — Minimal Result (current proposal)

```c
struct test_mailbox {
    uint32_t magic;
    uint32_t status;       /* running / pass / fail */
    uint32_t error_code;
    uint32_t detail0;
};
```

### Stage 2 — Phase-Aware Reporting

Add phase and step tracking so AEL can know exactly where the DUT stopped:

```c
struct test_mailbox {
    uint32_t magic;
    uint32_t status;
    uint32_t error_code;
    uint32_t detail0;
    uint32_t phase;        /* current test phase index */
    uint32_t step_id;      /* step within phase */
};
```

### Stage 3 — Diagnostic Reporting

Add measured vs. expected values to make failures self-describing:

```c
struct test_mailbox {
    uint32_t magic;
    uint32_t status;
    uint32_t error_code;
    uint32_t phase;
    uint32_t step_id;
    uint32_t measured;     /* actual observed value */
    uint32_t expected;     /* expected value */
    uint32_t flags;        /* observed peripheral/state flags */
    uint32_t timeout_count;
};
```

### Stage 4 — Standardized AEL Mailbox ABI

Define a reusable mailbox contract shared across all AEL DUT firmware:

- standardized struct layout with versioning
- canonical magic value and version field
- address/symbol policy for each supported MCU family
- lifecycle rules (when to write, what order, what to do after final write)

At this stage the mailbox becomes a first-class AEL interface, not a
per-project convention.

---

## 7. Design Choices

### 7.1 Fixed RAM Address vs. Linker Symbol

| | Fixed absolute address | Linker-defined symbol |
|---|---|---|
| **Pros** | Simple; ESP32JTAG needs no symbol awareness | Portable; survives memory map changes; integrates cleanly with build system |
| **Cons** | Fragile across MCUs with different RAM maps | Requires build system to export resolved address to ESP32JTAG |

**Recommendation:** Use a fixed address for the first experiment (simplest
path to proof-of-concept). For production use, adopt a linker-defined symbol
(`__ael_mailbox_start`) and require the build pipeline to export the resolved
address in the artifact manifest. This gives portability without requiring
ESP32JTAG to parse ELF files directly.

### 7.2 Polling vs. Halt-and-Read

ESP32JTAG could halt the target once and read the mailbox, or it could poll
periodically while the target runs. Continuous polling requires the debug
interface to support non-invasive memory access (not all targets support this
reliably).

**Recommendation for first version:** run DUT to completion, then halt/attach
and read mailbox once. This is the simplest and most reliable approach and
avoids timing and non-invasive access complications.

### 7.3 End-of-Test DUT Behavior

After writing the final status, the DUT needs to remain in a known, stable
state for readout. Options: infinite loop, software breakpoint, wait-for-halt
loop.

**Recommendation for first version:** infinite loop. It is the simplest, works
on all targets, and does not require debugger-specific instruction support.

---

## 8. Relationship to Existing GPIO Result Signaling

The mailbox mechanism does not need to replace GPIO-based reporting
immediately. A staged transition is appropriate.

| Phase | Approach |
|-------|----------|
| Now | Keep GPIO result signaling as-is; run mailbox proof-of-concept in parallel |
| After PoC validates | Use mailbox as the primary result path on boards where ESP32JTAG memory read is confirmed working; keep GPIO as a parallel fallback |
| After mailbox is validated on 3+ boards across 2+ MCU families | Make mailbox the default for all debug-capable targets; retire GPIO result signaling to fallback-only status |
| Long term | GPIO result signaling used only for non-debug-capable targets or as a redundant cross-check |

The transition gate is concrete: **mailbox validated on hardware across 3+
boards, 2+ families**. Until that gate is passed, both paths coexist.

---

## 9. Risks and Unknowns

### 9.1 ESP32JTAG Capability Gap

Reading target RAM over the debug path requires new support in ESP32JTAG. This
support does not exist today and must be implemented as part of the experiment.
The scope of that implementation is the primary unknown.

### 9.2 Reliability and Timing

Must verify:
- attach and halt timing after DUT enters its end-of-test loop
- memory read reliability (byte ordering, partial read behavior)
- whether halting the target is always acceptable at end of test
- behavior if ESP32JTAG attaches before DUT has written the final status

### 9.3 Cross-Target Portability

Different MCUs have different RAM base addresses, RAM sizes, and debug
behavior. The first experiment should not try to solve portability — it should
validate the concept on one known-good target (STM32G431CBU6) and address
portability in Stage 4.

### 9.4 Mailbox Contract Standardization

For this approach to scale, a standard mailbox ABI is eventually needed
(structure format, valid status values, address/symbol policy, lifecycle
rules). That standardization is deferred to Stage 4 and should not block the
first experiment.

---

## 10. Recommended Next Step

The best next step is a focused, minimal proof-of-concept — not full framework
integration.

**Proposed task:**

1. Write minimal mailbox firmware for STM32G431CBU6 (pass variant + fail
   variant)
2. Add minimal RAM read capability to ESP32JTAG (read N bytes from fixed
   address, return as structured data)
3. Run end-to-end: flash → run → attach → read mailbox → verify result
4. Confirm success criteria from Section 5

If the experiment succeeds, evaluate whether to generalize the mailbox
structure, standardize across MCU families, and integrate into AEL test
workflows. If it fails, record what failed and why before deciding whether to
continue.

---

## 11. Decision Framing

The immediate question is not:
> "Should all AEL tests switch to mailbox reporting right now?"

The immediate question is:
> "Should we run a focused experiment to prove this reporting path is viable?"

This experiment is small enough to attempt in a single session, but the
outcome matters: a working mailbox path would remove the GPIO result wiring
dependency and open significantly richer reporting for the entire AEL
validation system.

**Recommendation: yes, proceed with the experiment.**

---

## One-Sentence Summary

**AEL should evaluate a debug-mailbox result path in which DUT tests write
structured status into a fixed RAM location and ESP32JTAG reads that mailbox
over SWD/JTAG — reducing dependence on extra GPIO result wiring and enabling
richer, more robust automated result reporting.**
