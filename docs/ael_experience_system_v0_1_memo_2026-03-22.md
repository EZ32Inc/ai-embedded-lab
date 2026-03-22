# AEL Experience System v0.1 — Milestone Memo

**Date:** 2026-03-22

## What Changed

AEL now records, reuses, and grows from engineering experience across runs.

Three layers were built and connected in this session:

### 1. Experience Engine (external, unchanged)

Pre-existing at `/nvme1t/work/codex/experience_engine/`.
Stores structured Experience Units: `raw`, `intent`, `tags`, `outcome`, `confidence`, `avoid`, `actions`.
Provides `add()`, `query()`, `feedback()` API.

### 2. Civilization Engine (internal AEL module)

Location: `ael/civilization/`

The only layer in AEL that talks to the Experience Engine.
AEL never imports from experience_engine directly.

Call path:
```
pipeline.py
  → ael/civilization_client.py
    → ael/civilization/engine.py
      → experience_engine/api.py
```

**v0.1** (append-only): pre-run query + post-run record hooks in pipeline.

**v0.2** (aggregate update): run_index.json tracks `(board_id, test_name)` signatures.
Repeated runs strengthen existing EE records via `feedback("correct")` instead of appending duplicates.
New failure kinds create new records; same failure kind aggregates.

**v0.3** (before-run protocol + record_skill):
- `query_context()` now surfaces four sections before every run:
  1. run_stats — N runs, S success / F failed, confidence
  2. relevant_skills — known fix/decision skills for this board/domain
  3. likely_pitfalls — avoid_paths marked dangerous
  4. observation_focus — derived watch points
- `record_skill()` — new entry point, callable at any time during or after a run,
  no dependency on run-outcome sequence.

### 3. Experience Protocol (the "how experiences are produced")

Mapped from the existing three-layer spec (`ael_experience_accumulation_framework_v0_1.md`)
and seven-step bringup recording spec (`bringup_process_recording_spec_v0_1.md`):

```
Before run:  query_context()  →  run_stats + relevant_skills + pitfalls + observation_focus
During run:  record_skill()   →  callable at the moment of realization (no run-outcome gate)
After run:   record_run()     →  outcome + failure_kind (aggregate or new)
             record_skill()   →  if a fix was applied and worth preserving
```

`record_skill()` fields:
- `trigger` — when this skill applies (symptom / condition)
- `fix` — exact resolution (config, code, command)
- `lesson` — reusable rule derived from this experience
- `scope` — applicability scope (`stm32f4_discovery`, `all_stm32f4`, `stlink`, ...)
- `board_id` — specific board if narrower than scope
- `source_ref` — origin reference (bringup report, session note)

## Closed Experience Loop

```
AEL run
  → record_run()          [always, automatic]
  → record_skill()        [when a fix is realized, explicit]
  → query_context()       [next run on same board: skills surface before execution]
```

This is the closed loop. Skills from previous debugging sessions now appear before
the next run on the same board. The system improves with use.

## Initial Skills Seeded

Three known engineering quirks were seeded into the Experience Engine as the first
structured skills:

| scope | trigger | fix |
|-------|---------|-----|
| `stm32f4_discovery` | UART loopback fails silently on PA9/PA10 | Use USART2 on PD5/PD6 |
| `esp32jtag` | mcuInterface set to SPI breaks BMDA bit-bang SWD | Keep mcuInterface = GPIO |
| `stlink` | Target halted after GDB `load` — firmware does not execute | Add `monitor reset run` before `disconnect` |

These were previously only stored in AI memory files. They are now queryable via
`get_relevant_skills()` and will surface in `query_context()` before relevant runs.

## What This Is Not Yet

- No automatic skill extraction from logs (LLM-based summarization is a future step)
- No in-run checkpoint recording (stage boundaries captured only on failure via `failure_kind`)
- docs/skills/*.md files not yet batch-imported (natural ingestion via `record_skill()` preferred)

## Files Changed

| File | Change |
|------|--------|
| `ael/civilization/context.py` | Added `relevant_skills` field; `summary_lines()` now outputs four sections |
| `ael/civilization/engine.py` | `get_context()` populates `relevant_skills`; added `record_skill()` |
| `ael/civilization_client.py` | Exposed `record_skill()`; updated module docstring with protocol |
| `experience_engine/storage/memory.json` | 3 initial skills seeded |

## Terminology Correction (2026-03-22)

AEL has been using the word "test" for things like LED blinking, ADC sampling, UART
communication, and DAC waveform generation. This is incorrect — these are not tests.

**Correct model:**

| Old | New |
|-----|-----|
| test | embedded program |
| run test → pass/fail | run program → observe → adapt → evolve |
| test system | embedded program execution and evolution system |

**What changed (Phase 0 — output strings and docs):**
- `civilization/context.py` output: "no prior experience" → "no prior runs for program …"
- `civilization_client.py` output: "recorded run" → "program run recorded"
- `pipeline.py` output: "SKIPPED (test config)" → "SKIPPED (program config)"
- `inventory.py` display: "tests: none" → "programs: none"
- `docs/ael_one_pager.md`: "run tests on real hardware" → "run embedded programs on real hardware"

**Pack JSON (Phase 1 — backward-compatible):**
- Pack files now accept `"programs": [...]` as the preferred key
- Legacy `"tests": [...]` key still works (read as fallback)
- New packs should use `"programs"`

**Internal variables (Phase 2 — deferred):**
- `test_name`, `test_path`, `test_raw`, `test_kind` remain unchanged in code
- Will be migrated gradually without breaking callers
