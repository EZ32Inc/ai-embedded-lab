# AEL Experience Accumulation Framework v0.1

**Date:** 2026-03-16
**Status:** draft
**Reference case:** STM32F401RCT6 bringup session (2026-03-15)

---

## 1. Why Saving Only Results Is Not Enough

AEL already captures results well:

- `runs/*/result.json` — pass/fail, evidence, run ID
- `manifest.yaml verified: true` — board verified status
- `project.yaml` run links — which runs belong to which project

This is Layer A. It answers: **"Did it work?"**

But Layer A alone is a dead end for learning.

Consider two scenarios:

**Scenario A:** Board X passes all 8 experiments on first attempt.
Layer A records: `verified: true`. Nothing else is learned.

**Scenario B:** Board Y requires 3 rounds of debugging before passing.
Layer A records the same: `verified: true`. The debugging experience is lost.

In Scenario B, the engineer learned:
- which failure modes are common for this MCU family
- what the root causes were
- what the fix strategy was
- what rules generalize to future boards

Without Layer B and C, this knowledge exists only in the engineer's memory —
or in this case, only in the conversation log that gets discarded.

**AEL's long-term advantage is not just automation. It is accumulation.**
Every engineering session should make the next session faster and more reliable.

---

## 2. Three-Layer Memory Model

```
┌─────────────────────────────────────────────────────┐
│  Layer C — Experience                               │
│  "What pattern is reusable?"                        │
│  Skills / rules / policies / checklists             │
│  → stored in docs/skills/                          │
├─────────────────────────────────────────────────────┤
│  Layer B — Process                                  │
│  "What happened and why?"                           │
│  Debug log / bringup report / decision record       │
│  → stored in docs/specs/<board>_bringup_report.md  │
├─────────────────────────────────────────────────────┤
│  Layer A — Result                                   │
│  "Did it work?"                                     │
│  Pass/fail, evidence, run IDs, verified status      │
│  → stored in runs/, manifest.yaml, project.yaml    │
└─────────────────────────────────────────────────────┘
```

Each layer builds on the one below.
Layer A without B and C is just a scoreboard.
Layer B without C is a diary with no lessons drawn.
All three together create a system that improves with each engineering session.

---

## 3. Layer B — Process Record

### What belongs in a process record

A process record answers:

- What was the goal?
- What was attempted first?
- What failed, and what was the error message or observation?
- What was the root cause of each failure?
- What was changed, and why?
- What was the final working state?

### Template

Every board bringup should produce a process record at:
`docs/specs/<board>_bringup_report_v0_1.md`

Minimum sections:

```markdown
## Background and goal
## Problems encountered (one section per problem)
   ### Problem: <short name>
   - Symptom
   - Root cause
   - Fix
   - Lesson
## Final working state
## Candidate experiences for extraction (Layer C)
```

### Trigger

A process record should be written:
- After every new board bringup
- After any debugging session that required more than one round of iteration
- After any unexpected failure that required root cause analysis

It does NOT need to be written for clean first-pass runs with no surprises.

### Reference example

`docs/specs/stm32f401rct6_bringup_report_v0_1.md`

This document was written after the F401 session and covers:
- SPI SCK missing from wiring table
- `_sidata` undefined reference (linker script)
- GPIO signature 3-round debugging (LA window, toggle÷2, threshold)

---

## 4. Layer C — Experience Extraction

### What belongs in an experience record

A Layer C experience answers:

- What problem type was recognized?
- What is the generalizable pattern (not just this board, but any board)?
- What rule or strategy should be applied next time?
- What is the trigger condition for applying this rule?

### Format: Skill document

Each extracted experience becomes a Skill at:
`docs/skills/<topic>_skill.md`

Skill document structure:

```markdown
## Purpose
## Trigger (when to apply this skill)
## Core Rules (numbered, concise)
## How to apply (concrete steps or checklist)
## Reference case (link to Layer B document)
```

### Trigger for extraction

Extract a Skill when:
- The same problem type has appeared more than once, OR
- A problem required non-obvious diagnosis that wouldn't be found by inspection, OR
- A rule was learned that applies to a whole class of future work (not just this board)

Do NOT extract a Skill for:
- One-off quirks specific to a single board or configuration
- Problems already covered by an existing Skill

### Skills written so far (as of 2026-03-16)

| Skill | Extracted from |
|-------|---------------|
| `gpio_signal_threshold_skill` | F401 GPIO signature 3-round debug |
| `cmsis_startup_symbol_skill` | F401 `_sidata` linker error |
| `bench_wiring_completeness_skill` | F401 SPI SCK missing from wiring table |
| `banner_experiment_pattern_skill` | F401/F411 banner architecture design |
| `default_verification_repeat_skill` | Incorrect shell loop usage |

---

## 5. The Full Loop

```
Engineering session
        │
        ▼
┌───────────────┐
│  Layer A      │  Run completes → result.json, manifest, project links
│  Result       │
└───────┬───────┘
        │ if debugging / iteration occurred
        ▼
┌───────────────┐
│  Layer B      │  Write bringup report / debug log
│  Process      │  Document each problem, root cause, fix
└───────┬───────┘
        │ if generalizable pattern found
        ▼
┌───────────────┐
│  Layer C      │  Write Skill document
│  Experience   │  Trigger condition, rules, checklist
└───────┬───────┘
        │
        ▼
  Future sessions load Skills → fewer iterations → faster verified results
```

The loop closes when extracted Skills are actually applied in the next
similar session, reducing the number of rounds needed to reach Layer A.

---

## 6. Making the Loop Repeatable (Not Ad-Hoc)

The F401 bringup loop happened organically — the process record and
Skills were written after the session ended, prompted by conversation.
This works once but does not scale.

To make the loop systematic, AEL should:

### At session end (after any bringup or debugging session)

1. **Check Layer A:** Is `manifest.yaml verified: true`? Are run links recorded?
2. **Check Layer B:** Was a bringup report written? If not, and if iteration
   occurred, write one now using the template.
3. **Check Layer C:** Does the report's "candidate experiences" section contain
   items? If yes, evaluate each one against the extraction trigger criteria.
   Write Skills for those that qualify.

This check can be part of a future `ael session close` command,
or done manually at the end of each session using this document as a guide.

### Before a new bringup session

1. Load relevant Skills for the MCU family (e.g. STM32F4 → load CMSIS skill, GPIO threshold skill)
2. Review the wiring completeness checklist before touching hardware
3. Confirm `confirmed_facts` are captured before running (see startup clarification spec)

---

## 7. Relationship to Other AEL Specs

| Document | Relationship |
|----------|-------------|
| `confirm_before_generation_policy_v0_1.md` | Governs when to pause and confirm before generating code — feeds into Layer B trigger |
| `mcu_pin_verification_skill.md` | A Layer C skill applied at project start |
| `ael_project_startup_clarification_v0_1.md` | Companion spec — governs reality modeling at session start |
| `docs/skills/*` | The output of Layer C extraction |
| `projects/*/project.yaml` confirmed_facts | The structured reality record that intake feeds |

---

## 8. Open Items

- [ ] Define `ael session close` command (automate Layer A/B/C checklist)
- [ ] Define `ael project intake` command (write confirmed_facts from conversation)
- [ ] Add bringup report template as a file: `docs/templates/bringup_report_template.md`
- [ ] Add Layer B/C trigger to new_board_bringup_skill.md as a required final step
