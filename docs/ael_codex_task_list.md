# AEL Codex Task List — Architecture Mapping and One-Run Trace

## Goal

Create a minimal but useful architecture map for the current AEL repo, then trace one real execution path end-to-end using an existing stable demo/case.

This is **not** a large refactor.  
This is a **small documentation and repo-understanding task** to help future development.

---

## Deliverables

Create these two files under `docs/`:

1. `docs/architecture_map.md`
2. `docs/trace_one_run.md`

Do **not** over-engineer them.  
They should be practical working docs, short and accurate.

---

## Task 1 — Create `docs/architecture_map.md`

### Objective
Produce a compact map of the current system that answers:

- What are the main AEL components now?
- How do components call or communicate with each other?
- Which parts are core orchestration/scheduling, and which parts are adapters/plugins?

### Instructions

Inspect the current repo and create `docs/architecture_map.md`.

Keep it concise, roughly one short page.  
Prefer accuracy over completeness.

### Required content

Include these sections:

#### 1. Entry points
Identify the current entry points of the system, for example:

- main program
- CLI entry
- server entry
- orchestrator entry
- agent runner entry

For each entry point, list:

- file path
- function/class name if applicable
- brief purpose

#### 2. One run lifecycle
Describe the current execution lifecycle in AEL, using the best match to the current codebase.

Target shape:

- receive task
- prepare context/spec
- generate code or plan
- build
- flash
- verify
- retry if needed
- report result

For each step, map it to the file(s)/module(s) that currently implement it.

#### 3. Main components
List major components/modules and what they do.

Example categories:

- orchestrator
- task queue
- agent runner
- Codex integration
- build runner
- flash runner
- verification/instrument layer
- reporting/logging
- profile/case definition
- board/tool adapters

Use the actual repo structure, not guessed architecture.

#### 4. Communication/call relationships
Briefly describe how components interact, such as:

- direct Python function calls
- subprocess calls
- JSON files
- config files
- HTTP/WebSocket
- serial/JTAG/OpenOCD/instrument APIs
- log/result artifacts

A simple bullet list is enough.

#### 5. Core vs adapter split
Make a short section:

- **Core orchestration**
- **Adapters / board-specific / tool-specific layers**

Place each relevant module or directory into one of those categories.

### Constraints

- Do not redesign the architecture.
- Do not rename files.
- Do not add diagrams unless easy and fast.
- Do not invent components that do not exist.
- If something is unclear, mark it as:
  - `Unknown`
  - `Needs confirmation`
  - `Appears to be ...`

---

## Task 2 — Create `docs/trace_one_run.md`

### Objective
Trace one real, representative AEL run from input to exit.

Use one stable existing case. Prefer one that already works reliably, such as:

- ESP32S3 Golden GPIO test
- RP2040 PICO Golden GPIO + ESP32JTAG as Instrument test

### Instructions

Run or inspect one real case and create `docs/trace_one_run.md`.

This file should show the actual call chain, not a theoretical design.

### Required content

Include these sections:

#### 1. Selected case
State which case was traced.

Include:

- case/profile name
- relevant config/spec file path(s)
- why this case was chosen

#### 2. Run input
Document the actual input to the run, such as:

- CLI command
- config/profile
- task spec / prompt / case definition
- environment assumptions if needed

#### 3. End-to-end call chain
From entry to exit, list the call chain in order.

Use this style:

1. entry point invoked: `path/to/file.py:function_name`
2. task loaded from: `...`
3. agent runner called: `...`
4. Codex or generation step invoked: `...`
5. build step invoked: `...`
6. flash step invoked: `...`
7. verify step invoked: `...`
8. retry/report/result written: `...`

For each step, include:

- file path
- function/class/script if known
- one-line purpose

#### 4. Artifacts produced during the run
List what files, logs, temp outputs, or reports are generated.

Examples:

- build logs
- generated code
- result JSON
- flash logs
- verification logs
- final summary/report

Use actual artifacts from the current repo behavior if available.

#### 5. Observed control points
Identify where the important control decisions happen, such as:

- retry decision
- pass/fail judgment
- choosing build target
- choosing flash method
- selecting verification flow
- writing final result

This section is important because it shows where the “real orchestrator logic” lives.

#### 6. Gaps / unclear areas
Add a short section listing unclear points, dead ends, or places where behavior is implicit or scattered.

Example:

- retry logic appears split across two modules
- flash result parsing is indirect
- verification outcome is not centralized
- case spec format is partly implicit

---

## Task 3 — Keep the docs practical

### Formatting rules

- Use Markdown only.
- Keep each file readable and compact.
- Use code fences for commands and paths when helpful.
- Prefer bullet points and short sections.
- No big essays.

### Accuracy rules

- Base everything on the existing repo.
- If you infer something, label it clearly as inference.
- Do not pretend uncertain things are confirmed facts.

---

## Task 4 — improvement needed 

During creating the doc above, give me a list of waht needs to be improved or changed

Add a short section to `docs/architecture_map.md`:

## Immediate pain points noticed

List issues discovered while mapping the repo, for example:

- entry points are scattered
- retry logic is duplicated
- build/flash/verify boundaries are blurry
- adapter vs orchestration code is mixed

Add a short section to `docs/architecture_map.md`:

---

## Non-goals

Do **not** do these in this task:

- no architecture rewrite
- no module moves
- no large refactor
- no protocol redesign
- no schema redesign
- no new framework introduction
- no broad cleanup unrelated to the two docs

---

## Expected output summary

At the end of the task, the repo should contain:

- `docs/architecture_map.md`
- `docs/trace_one_run.md`

Both files should be short, concrete, and based on the current implementation.

---

## Suggested working approach

1. Inspect repo structure.
2. Identify current entry points.
3. Identify the run lifecycle modules.
4. Choose one stable real case.
5. Trace the actual call path.
6. Write `docs/architecture_map.md`.
7. Write `docs/trace_one_run.md`.
8. Keep unknowns explicitly marked instead of guessing.

---

## Final note for Codex

This task is meant to improve visibility into the current AEL system, not to change behavior.

The result should help a human or future AI answer:
- where does a run start?
- what happens during a run?
- where is orchestration logic centralized?
- where are board/tool-specific adapters?
- what should be cleaned up later, based on evidence rather than guesswork?

