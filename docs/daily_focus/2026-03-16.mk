# AEL Daily Focus — 2026-03-16

## Theme
**Deepen the foundation: strengthen reality modeling, formalize experience accumulation.**

Today is not about adding boards or features.
It is about making AEL more reliable, more reality-aware, and more capable of improving itself.

---

## Codebase Reality Check (morning assessment)

### What already exists

| Layer | Status | Evidence |
|-------|--------|---------|
| Layer A — Result record | **Complete** | `runs/*/result.json`, `manifest.yaml verified:true`, project run links |
| Layer B — Process record | **Partial, ad-hoc** | `stm32f401rct6_bringup_report_v0_1.md` exists but no template or trigger |
| Layer C — Experience extraction | **Partial, ad-hoc** | 5 Skills in `docs/skills/` but no formal extraction process |
| Reality clarification policy | **Partial** | `confirm_before_generation_policy_v0_1.md`, `mcu_pin_verification_skill.md`, `project questions` exist |
| confirmed_facts structured intake | **Missing** | No command to write facts from conversation into project.yaml |

### Key gap
The biggest gap bridging both today's focus and `next_session_plan.md` Priority 1:

> When a user describes their real bench setup in conversation,
> there is no structured path to capture it into `confirmed_facts`.
> AEL currently infers or guesses — which is the root cause of "confident but wrong" behavior.

---

## Today's Work Plan

### Morning — Two documents (concepts before code)

#### Document A: AEL Process → Experience → Skill Framework
File: `docs/specs/ael_experience_accumulation_framework_v0_1.md`

Answer these questions:
- Why saving only results (Layer A) is not enough
- What belongs in a process record (Layer B) — define a template
- How experience is extracted (Layer C) — define trigger conditions and format
- How extracted experience becomes a Skill / rule / policy
- How to make this loop repeatable (not ad-hoc like yesterday)

Note: Yesterday's F401 bringup was a good organic example of this loop.
Use it as the reference case in the document.

#### Document B: AEL Real-Project Startup Clarification Spec
File: `docs/specs/ael_project_startup_clarification_v0_1.md`

Answer these questions:
- Why repo-example assumptions are dangerous (use F401 SPI SCK incident as example)
- What minimum information must be confirmed before execution
- How AEL should behave when setup information is incomplete
- How to shift from "I know a similar example, so I proceed" to "I confirm first, then proceed"

Minimum information checklist (starting point):
- MCU / board identity (dev board or custom?)
- Flash / programming method
- Instrument: which one, IP, connected pins
- Observable signals (which DUT pins → which instrument channels)
- Board-side loopbacks in place
- Success criteria for each experiment

---

### Afternoon — One implementation push

**Choose Option 1: confirmed_facts structured intake**

Reason: This is the most concrete, immediately actionable item.
The `confirmed_facts` data structure already exists in `project.yaml`.
The `project questions` command already shows what needs confirming.
The missing piece is a command that writes answers into the project.

Proposed command:
```bash
python3 -m ael project intake --project <name>
```

Behavior:
1. Reads the project's current `confirmed_facts` and identifies gaps
2. Asks the user structured questions for each missing fact
3. Validates answers against board config and test plan requirements
4. Writes confirmed answers into `projects/<name>/project.yaml`

This directly improves the reality modeling loop and makes run-gate more reliable.

---

### Strategic memo (write when time allows)

**Parallel design-space exploration** — `docs/specs/ael_parallel_exploration_strategy_v0_1.md`

Key ideas to capture:
- AEL should explore many candidate paths in parallel, not one at a time
- Enabling pieces needed: task decomposition, worker orchestration, result aggregation, experience feedback
- This is a long-term direction; document it now so it informs near-term architecture decisions

---

## What NOT to do today
- Add more boards
- Chase broader coverage
- Go deep into cloud-scale architecture details
- Start multiple implementation directions at once

---

## Definition of success
Today is successful if:
- Document A (experience framework) is written and committed
- Document B (startup clarification spec) is written and committed
- `project intake` command design is agreed (spec written, implementation started or complete)
- The system is conceptually clearer and better positioned to accumulate knowledge

---

## One-sentence summary
**Today's best move: formalize the process→experience→skill loop, and build the confirmed_facts intake command.**
