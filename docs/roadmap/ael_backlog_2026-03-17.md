# AEL Backlog — 2026-03-17

Items recorded for future sessions. Not blocking current work.

---

## 1. Experience Accumulation — `ael session close`

**Spec:** `docs/specs/ael_experience_accumulation_framework_v0_1.md`,
`docs/specs/bringup_process_recording_spec_v0_1.md`

**What's missing:** Framework (Layer A/B/C) is fully specified but not enforced
by CLI. Bringup reports and skill extraction happen ad-hoc.

**Minimal implementation:**
- `ael session close` command
- Checks `manifest.yaml verified: true` (Layer A)
- Prompts for bringup report if iteration occurred (Layer B)
- Lists candidate skills for extraction based on trigger criteria (Layer C)

---

## 2. Bench Wiring Auto-Discovery

**Spec:** `docs/specs/bench_wiring_auto_discovery_spec_v0_1.md`

**Problem:** User-provided wiring descriptions are hints, not truth. STM32G431
bringup hit this: assumed PA2→P0.0, real connection was PA2→P0.3. Wasted
debug cycles on firmware before discovering the mismatch.

**Solution:** Multi-frequency probe firmware (PA2/PA3/PA4/PB3 at 1:2:4:8 Hz
ratio). One run discovers real P0 mapping. Compare against user-stated wiring;
flag discrepancy before any firmware generation begins.

**Scope:**
1. Extend probe firmware to emit per-pin frequency signatures
2. Auto-infer mapping from captured frequencies
3. Compare vs. confirmed_facts; block run-gate if mismatch

---

## 3. Parallel Exploration Strategy

**Spec:** `docs/specs/ael_parallel_exploration_strategy_v0_1.md`

**Concept:** Generate multiple firmware variants (clock configs, polarity,
DMA/polling) in parallel, test all, aggregate results to identify root cause
faster than sequential debugging.

**Current state:** Architecture designed, not implemented. Existing run/pack/result
model is extensible to support it.

**Minimal steps (in order):**
1. Define `exploration pack` format (`mode: exploration` + hypothesis set)
2. Implement `ael run diff` (compare signal characteristics between two runs)
3. Multi-worker orchestration (reuses instrument locking)
4. Auto-hypothesis generation from a failing run

---

*Recorded by: session 2026-03-17. Not assigned. Priority: medium-term.*
