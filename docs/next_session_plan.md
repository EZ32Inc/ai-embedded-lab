# Next Session Plan

**Prepared:** 2026-03-15 (end of session)
**Context:** STM32F401RCT6 bringup complete, promoted to verified board.

---

## Current System State

### Verified Boards (default verification: 4/4, 10-round stable)

| Board | Experiments | Status |
|-------|-------------|--------|
| ESP32-C6 DevKit | gpio_signature_with_meter | verified |
| RP2040 Pico | gpio_signature | verified |
| STM32F411CEU6 | 8 experiments | verified |
| STM32F401RCT6 | 8 experiments | verified ← completed today |

### Skills Added Today

| Skill | File |
|-------|------|
| GPIO signal threshold | `docs/skills/gpio_signal_threshold_skill.md` |
| Default verification repeat | `docs/skills/default_verification_repeat_skill.md` |
| CMSIS startup symbol check | `docs/skills/cmsis_startup_symbol_skill.md` |
| Bench wiring completeness | `docs/skills/bench_wiring_completeness_skill.md` |
| Banner experiment pattern | `docs/skills/banner_experiment_pattern_skill.md` |

---

## Priority 1: confirmed_facts Structured Intake

### Problem

The current gap in the system: when a user describes their real bench
setup in conversation (wiring, instrument IP, loopbacks), there is no
structured path to write that information into `confirmed_facts`.
It currently requires manual editing or AI guesswork.

This causes AI to sometimes assume wiring matches existing reference
cases, leading to "confident but wrong" behavior.

### Why This Matters

- New board bringup depends on accurate confirmed_facts for run-gate to pass
- Without structured intake, facts come from AI inference → risk of diverging from reality
- Fixing this makes every future bringup more reliable and less dependent on manual correction

### Proposed Approach

Design a `project intake` command (or conversation-driven flow) that:

1. Asks the user structured questions about their bench:
   - Which instrument? (IP / instance name)
   - Which pins are connected to which instrument channels?
   - Which loopbacks are in place?
2. Validates answers against board config and test plan requirements
3. Writes confirmed answers directly into `projects/<name>/project.yaml`
   under `confirmed_facts`

**Starting point for design discussion:**
- Look at existing `confirmed_facts` structure in `projects/stm32f401rct6_bringup/project.yaml`
- Look at `project questions` command output for a mature path board
- Identify which facts are currently written manually vs inferred

---

## Priority 2: Draft Board Promotion

Two boards in `assets_branch/duts/` are in draft state:

| Board | Status | Notes |
|-------|--------|-------|
| `stm32f401ce_draft` | draft | Different flash size variant of F401 |
| `stm32f407vg_draft` | draft | F407, larger package, more peripherals |

These can follow the same bringup path as F401RCT6.
Prerequisite: hardware available and connected.

---

## Priority 3: Session Log Commit

`docs/session_log_20260315.md` was written today but not committed
(user requested no commit). Decide whether to commit or discard at
start of next session.

---

## Quick Start for Next Session

1. Run default verification to confirm baseline is still healthy:

```bash
python3 -m ael verify-default run
```

2. Check open items:

```bash
cat docs/next_session_plan.md
```

3. Start with Priority 1 (confirmed_facts intake design) — discuss
   approach before writing any code.

---

## Reference Commits (today's work)

| Commit | Summary |
|--------|---------|
| `05f3077` | Add F401 full 8-experiment suite |
| `86c7af7` | Mark F401 verified: 8/8 PASS |
| `51d02a5` | Replace F103 with F401 in default verification |
| `bd0f8ab` | Promote F401 to verified board status |
| `86abe82` | Add default_verification_repeat_skill |
| `39f202b` | Add GPIO threshold skill + debug log |
| `da9cd71` | Add F401 complete bringup report |
| `55294a0` | Add S1/S2/S3 skills, correct bringup report |
