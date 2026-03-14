# AEL User Question Layer v0.1

## Draft for review against current codebase

---

## 1. Purpose

This document proposes a lightweight, AI-first approach for the next stage of AEL user-facing project management.

The goal is **not** to build a heavy project-management system, a large UI framework, or a rigid database model.

Instead, the goal is to define:

1. **what users most naturally want to ask**,
2. **how AEL should answer those questions consistently**, and
3. **what minimal data/state layer is needed to support those answers**.

This approach assumes that:

- users interact primarily through natural language,
- AI is the main retrieval and summarization layer,
- files remain important, but should not be the primary user-facing abstraction,
- the system should stay lightweight and be allowed to grow naturally over time.

---

## 2. Core Product Direction

The next AEL stage should shift from primarily expanding capability coverage to improving:

- user project management,
- user-facing workflow clarity,
- system maturity and stability,
- AI-first interaction design.

The key design change is this:

> The user interface is no longer primarily a button/menu/page problem.
> It is increasingly a **question design + answer design + state design** problem.

Users will not naturally think first in terms of folders, file trees, or internal object names.
They will naturally ask things like:

- What project am I currently working on?
- Is this project healthy right now?
- What is the current blocker?
- What was the last successful run?
- What has already been validated?
- What is the best next step?
- What did we learn last time before stopping?

Therefore, AEL should optimize first for answering those questions well.

---

## 3. Scope of v0.1

This draft intentionally aims for a **minimal, lightweight first implementation**.

It does **not** propose:

- a heavy project database,
- a complete UI/dashboard system,
- a complex workflow engine,
- automatic logging and clustering of all user questions,
- a large ontology of project/entity relationships.

Instead, v0.1 proposes four things:

1. a small set of high-frequency user questions,
2. standard answer structures for those questions,
3. a minimal state/data model to support them,
4. simple retrieve/write guidelines for AI.

Important v0.1 implementation note:

- v0.1 should be **derived-state first**
- it should not assume that AEL already has a committed, first-class stored state layer for all project questions
- in many cases, the first useful state object may be derived from current config, inventory output, current capability docs, and recent closeout/repeat notes
- only after that proves useful should AEL decide whether additional committed state objects are needed

---

## 4. Design Principles

### 4.1 Keep it lightweight

Do not over-model the system.
Do not try to encode every possible project concept up front.
Use only the minimum structure needed to answer the most important questions reliably.

### 4.2 Preserve natural growth

`default verification` should remain a living, system-owned baseline object.
It should continue to grow naturally.

User project support should grow alongside it, not replace it.

### 4.3 Files are important, but not the main user abstraction

Files remain essential project assets:

- source files
- plans
- configs
- profiles
- docs
- run artifacts
- evidence
- reports

But the user should not need to navigate raw file trees in order to understand project state.

The file system should serve primarily as the **asset layer beneath the question/state layer**.

That means:

- files remain the durable backing assets for code, configs, evidence, and notes,
- users should not need raw file-tree navigation as the primary interaction mode,
- AI and the question/state layer should be the first retrieval and summarization surface,
- file layout should remain lightweight and allowed to evolve naturally,
- detailed file-layout decisions can be deferred until after the first question/state layer review.

### 4.4 AI-first interaction

The system should assume:

- users ask questions in natural language,
- AI retrieves and synthesizes the answer,
- AI can also suggest useful questions to ask next.

### 4.5 Clear authority

For each important question, there should be a clear primary data source.
Avoid situations where multiple sources appear equally authoritative.

---

## 5. Primary Goal

The immediate goal is:

> Make AEL reliably answer the highest-value user questions using a lightweight, structured project/state layer plus existing docs/history.

This means the first success criterion is not “more UI” or “more objects.”
The first success criterion is:

- users can ask the most important project questions,
- AEL can answer them accurately,
- answers are stable in structure and meaning,
- the backing state remains simple and maintainable.

---

## 6. Secondary Goal

The second goal is:

> Enable guided questioning.

The system should not only answer questions.
It should also be able to suggest the most useful next questions, for example:

- Do you want the current project status?
- Do you want the last stopping summary?
- Do you want the current blocker?
- Do you want the best next step?
- Do you want the latest validated test list?

This is effectively the first AI-first user interface layer.

---

## 7. Recommended v0.1 Implementation Strategy

The recommended first implementation is based on four layers:

### Layer A: High-frequency user questions

Define a small set of common user questions.
Start with approximately 10–20 questions.

### Layer B: Standard answer structures

For each question type, define a stable answer structure.
Not a fixed answer, but a fixed answer shape.

### Layer C: Minimal state/data layer

Create a small number of structured state objects to support the most important answers.

### Layer D: Retrieve/write guidelines

Define how AI should:

- choose data sources,
- prioritize current state vs history,
- write back important updates,
- avoid drift and inconsistency.

---

## 8. High-Frequency Questions (Initial Draft)

### 8.1 Project state questions

1. What project am I currently working on?
2. What is the current status of this project?
3. Is this project healthy right now?
4. What is the current blocker?
5. What is the best next step?

### 8.2 Recent-result questions

6. What was the last successful run?
7. What failed most recently?
8. What did we validate most recently?
9. What did we learn last time before stopping?

### 8.3 Validation/capability questions

10. Which tests are already validated for this board/project?
11. What is included in default verification right now?
12. Is this board already part of default verification?
13. What is the current status of board X?

### 8.4 Evolution/history questions

14. Why was this change made?
15. When did this board/test become stable?
16. What was the root cause of the previous failure?

### 8.5 Guided workflow questions

17. What should I ask next?
18. What should I check before continuing?
19. What is the safest next validation step?
20. What should I review before adding this board/test into baseline?

---

## 9. Standard Answer Structures (Initial Draft)

Below are recommended answer shapes, not rigid templates.

### 9.1 “What is the current status of this project?”

Recommended answer structure:

- Current project name
- Current health/status summary
- Current blocker (or “none known”)
- Last successful run
- Most recently validated capability
- Best next recommended action
- Key references (if needed)

Health/result interpretation should distinguish:

- `PASS`
- `FAIL`
- `INVALID`

Where:

- `PASS` means the intended live validation completed successfully,
- `FAIL` means the intended live validation ran and found a real failing condition,
- `INVALID` means the attempted run did not produce a valid bench verdict, for example because of sandbox/network blocking, unreachable live bench infrastructure, or a broken execution context before the intended validation could occur.

### 9.2 “What is the current blocker?”

Recommended answer structure:

- Blocker summary
- Classification (build / bench / transport / DUT / verification / unknown)
- Why that is the current blocker
- Evidence/source
- Best next step

### 9.3 “What was the last successful run?”

Recommended answer structure:

- Run name / test name
- Run ID
- What it proved
- Whether it changed project confidence materially
- Relevant references

### 9.4 “What did we learn last time before stopping?”

Recommended answer structure:

- Concise stopping summary
- What was proven
- What remains unresolved
- Recommended restart point
- Key notes/docs to read

### 9.5 “What is included in default verification right now?”

Recommended answer structure:

- Current default-verification steps
- Which are passing/known-good
- Any known current blocker affecting overall suite health
- Whether a newly added step is already validated in live default verification

### 9.6 “What is the current status of board X?”

Recommended answer structure:

- Board identity
- Current capability status
- Validated tests
- Whether it is part of default verification or smoke packs
- Repeat evidence status
- Best next action, if any

---

## 10. Minimal State/Data Layer

The v0.1 state layer should stay small.

It should **not** attempt to model everything.
It only needs to support the highest-value questions.

### 10.1 Recommended structured state objects

At minimum, support these object types:

1. **System-owned baseline object**
   - example: `default verification`
   - current AEL reality: this already has strong natural authority sources in config, runtime, and review docs

2. **Board/capability object**
   - example: `stm32f411ceu6`
   - current AEL reality: this is already partly represented by DUT inventory, capability notes, bring-up reports, and repeat-validation notes

3. **User project object**
   - example: a future `ProjectXYZ`
   - current AEL reality: this is future-facing and should not be over-modeled in v0.1

### 10.2 Minimal state fields

Recommended minimal fields:

- `name`
- `type`
- `board` or DUT identity
- `active_suite`
- `health_status`
- `current_blocker`
- `last_successful_run`
- `validated_tests`
- `next_recommended_action`
- `key_refs`

Optional later fields may be added, but these are enough for v0.1.

Important scope note:

- for v0.1, AEL should prioritize the first two object types:
  - system baseline object
  - board/capability object
- user project objects are still valuable, but they are the least mature part of the current repo reality and should remain future-facing in the first implementation

### 10.3 Relationship between state and the file system

The state layer should not replace the file system.

Instead:

- the file system remains the underlying asset store,
- lightweight state objects point users and AI toward the right current assets,
- narrative docs remain important for explanation and historical meaning,
- the question/state layer sits above files and helps avoid raw file-tree navigation as the default user workflow.

This keeps v0.1 practical:

- no heavy database is required,
- no rigid asset model is required up front,
- existing repo assets remain usable,
- and the exact file layout can keep evolving while the question/state layer is reviewed.

### 10.4 Derived-state first

In current AEL, the most realistic first implementation is often a **derived state object**, not a newly invented stored state file.

Examples:

- a `default verification` state object can be derived from:
  - current default-verification config,
  - runtime/default-verification code paths,
  - recent default-verification review docs,
  - current validated capability summary
- a board/capability state object can be derived from:
  - DUT inventory,
  - `inventory describe-test`,
  - capability anchor notes,
  - bring-up reports,
  - repeat-validation notes

This keeps v0.1 aligned with current repo reality:

- answer quality can improve before a new storage layer exists,
- authority remains visible,
- duplication is minimized,
- and AEL can defer creating committed state files unless they prove clearly useful.

### 10.5 Example conceptual state object

```json
{
  "name": "Default Verification",
  "type": "system_baseline",
  "health_status": "partial_pass",
  "current_blocker": "esp32c6 flash/serial path issue",
  "last_successful_run": {
    "step": "stm32f411_gpio_signature",
    "run_id": "2026-03-14_09-29-06_stm32f411ceu6_stm32f411_gpio_signature"
  },
  "validated_tests": [
    "rp2040_gpio_signature",
    "stm32f103_gpio_signature",
    "stm32f103_uart_banner",
    "stm32f411_gpio_signature"
  ],
  "next_recommended_action": "stabilize esp32c6 flash/serial path and rerun default verification",
  "key_refs": [
    "configs/default_verification_setting.yaml",
    "docs/default_verification_baseline.md"
  ]
}
```

This is only an example shape, not a fixed required schema.

---

## 11. Narrative Notes Layer

Structured state should be complemented by human-readable notes, typically in Markdown.

Recommended note types:

- closeout notes
- bring-up reports
- repeat-validation notes
- stopping summaries
- lessons learned
- capability anchor notes

These notes are important because structured state alone cannot capture:

- richer explanation,
- reasoning,
- root-cause narrative,
- tradeoffs,
- operator guidance.

The intent is not to replace files with state.
The intent is to make files easier to use by placing a lightweight AI-first question/state layer above them.

---

## 12. Data Source Priority Guidelines

To keep the system lightweight and stable, AI should use simple source-priority rules.

### 12.0 Compact authority map for high-frequency questions

Recommended current authority map:

| Question | Primary authority | Secondary authority |
| --- | --- | --- |
| What DUTs/tests exist right now? | `python3 -m ael inventory list` | current DUT inventory AI references |
| What are the connections/setup for test X? | `python3 -m ael inventory describe-test --board <board> --test <test>` | board config + test plan |
| What is included in default verification right now? | `configs/default_verification_setting.yaml` | `python3 -m ael verify-default run` and default-verification docs |
| Is board X already part of default verification? | `configs/default_verification_setting.yaml` | current default-verification review docs |
| What is the current status of board X? | current capability anchor / bring-up closeout / repeat-validation note | DUT inventory and describe-test |
| What was the last successful run? | most recent closeout / repeat-validation / result note | run artifacts under `runs/` |
| What is the current blocker? | latest closeout / repeat note / current validated capability summary | latest run evidence and operator notes |

This table should stay lightweight.
It is meant to make current authority obvious, not to define a large permanent ontology.

### 12.1 For current-state questions

Recommended priority:

1. derived or stored state object, if one exists and is current
2. current config/current active status docs
3. most recent summary/closeout/repeat note
4. git history / older historical docs

Principle:

> Prefer current authority before historical explanation.

### 12.2 For reason/history questions

Recommended priority:

1. recent closeout/report/summary note
2. git history
3. older archived reviews/references

Principle:

> Prefer explanation docs first, then history.

---

## 13. Write Rules (Minimal v0.1)

AI write behavior should also remain limited and simple at first.

Recommended allowed write targets:

### 13.1 Structured state updates

AI may update fields such as:

- `health_status`
- `current_blocker`
- `last_successful_run`
- `validated_tests`
- `next_recommended_action`

If no committed state object exists yet, AI may instead update the narrative or closeout layer that currently serves as the effective state authority.

### 13.2 Summary/note documents

AI may write or update:

- repeat-validation notes
- closeout notes
- stopping summaries
- capability notes

### 13.3 Avoid broad freeform write-back in v0.1

Do **not** begin with a model where AI freely mutates many overlapping records without clear authority.

Keep writeback narrow and explicit.

---

## 14. Default Verification and User Project Relationship

`default verification` should remain a first-class system-owned baseline object.

It should not be removed or conceptually discarded.

Instead:

- `default verification` continues as the system baseline line,
- user projects grow alongside it,
- both can eventually use similar question/answer/state mechanisms,
- but they should not be forced into the exact same role.

This is a natural-growth model, not a replace-everything model.

Current repo reality:

- `default verification` already behaves like a real system-owned baseline object
- board/capability objects are already partly real through DUT inventory plus closeout/capability notes
- user project objects are not yet equally mature and should not drive the first v0.1 implementation

---

## 15. Guided Question Layer

Once A and B are defined, the first AI-first user interface can be implemented as a set of suggested questions.

Examples:

- Do you want the current project status?
- Do you want the latest stopping summary?
- Do you want the current blocker?
- Do you want the next recommended action?
- Do you want the validated test list?

This is likely more valuable in the near term than building a heavy UI.

---

## 16. What Not to Do Yet

For v0.1, it is recommended **not** to do the following yet:

- full project database design
- automatic recording and clustering of all user questions
- broad freeform memory layer for all interactions
- complex dashboard-first design
- heavy workflow engine
- large ontology/schema design

These may become valuable later, but would likely slow down the current stage.

---

## 17. Immediate Next Steps

### Step 1
Finalize the high-frequency question list.

### Step 2
Finalize standard answer structures for each question class.

### Step 3
Map each question to its primary data source.

### Step 4
Define one minimal state-object shape for:

- default verification,
- one board/capability object,
- one future user project object.

### Step 5
Define simple retrieve/write guidelines.

### Step 6
Implement a first guided-question layer.

### Step 7
Review whether the initial question/state layer is already sufficient before introducing any heavier file-layout or storage-layer redesign.

### Step 8
Only after the first review, decide whether any additional file-system organization is actually needed.

---

## 18. Review Questions for Codex

When reviewing this draft against the current codebase, Codex should answer:

1. Which existing files/docs/configs already cover the needed current-state data?
2. What is the lightest realistic way to represent a minimal state object in the repo?
3. Which current docs already function as narrative notes?
4. Where are the authority conflicts today, if any?
5. What can be implemented first with minimal disruption?
6. What should remain unchanged because it already works naturally (especially around default verification)?
7. What is the smallest useful first implementation for a question-backed project state layer?

---

## 19. One-Sentence Summary

AEL should not begin its next user-facing phase by building a heavy project-management system.
It should begin by building a lightweight **AI-first user question layer**, supported by minimal structured state, existing narrative docs, and simple retrieve/write rules.
