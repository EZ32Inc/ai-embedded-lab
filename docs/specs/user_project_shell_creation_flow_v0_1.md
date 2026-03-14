# User Project Shell Creation Flow v0.1

## Purpose

This document defines the smallest realistic v0.1 flow for the first
user-project creation case in AEL.

The concrete scenario is:

> "I have a board using `stm32f411ceu6`. Please create a first example project
> for me."

This flow is intentionally lightweight.

It does **not** introduce:

- a heavy project-management system
- a broad database model
- a full workflow engine
- code generation as the first step

Instead, it defines a thin AI-first project shell that sits above the current
system baseline and board/capability layers.

## Core Design Rule

For v0.1, user-project creation should proceed in three stages:

1. create a lightweight empty-shell user project
2. clarify setup, wiring, validation approach, and desired example
3. only then propose code generation / build / flash / verify

This keeps user-project creation aligned with current AEL reality:

- mature board capability paths already exist
- setup discussion is often more important than immediate code generation
- AI should manage state lightly rather than invent a large project model

## First Concrete v0.1 Scenario

The initial supported-or-similar scenario is:

- the user board is already supported by AEL, or is highly similar to a mature
  supported path
- `stm32f411ceu6` is the worked example because it is currently a mature,
  repeat-validated path in AEL

The "unknown new board" case is intentionally deferred.

## Minimal Flow

### Step 1: Create project shell

When the user asks to create a first project for a supported-or-similar board:

- create a lightweight project folder under `projects/`
- record the user goal
- resolve the closest mature board/capability path
- record confirmed facts
- record assumptions
- record unresolved items
- recommend the best next questions

Do **not** generate firmware code yet unless the user explicitly asks to skip
the setup discussion.

### Step 2: Clarify setup and intent

After the shell exists, the next AI step should discuss:

- exact board/module identity if still relevant
- wiring/setup available on the user's bench
- validation approach
- what first example the user actually wants
  - blink
  - gpio signature
  - uart
  - adc
  - spi
  - other

This stage should behave similarly to current AEL bring-up/debug work:

- isolate assumptions
- restate setup clearly
- separate confirmed facts from inferred ones
- recommend the safest next validation step

### Step 3: Propose generation and validation

Only after setup and intent are clear should AEL propose:

- code generation
- build
- flash
- live verify

At that stage, the project shell provides the user-facing context, while the
board/capability layer remains the technical authority.

## Lightweight File-System Placement

The lightest natural repo placement is:

- `projects/<project_id>/`

Example:

- `projects/stm32f411_first_example/`

This keeps user projects:

- clearly separate from system-owned baseline/config assets
- close to the rest of the repo
- easy to inspect without forcing a new storage design

The file system remains the asset layer.
The user-project shell is only a thin question/state layer above it.

## Minimum Project Metadata

The project shell should start with one small metadata file:

- `project.yaml`

Recommended fields:

- `project_id`
- `project_name`
- `project_type`
- `user_goal`
- `target_mcu`
- `closest_mature_ael_path`
- `status`
- `confirmed_facts`
- `assumptions`
- `unresolved_items`
- `current_blocker`
- `last_action`
- `next_recommended_action`
- `key_refs`

This is enough for v0.1.

## Initial Files

Generate only these initially:

1. `project.yaml`
2. `README.md`
3. `session_notes.md`

These files are enough to support:

- "what did you create?"
- "what mature path is this based on?"
- "what is assumed vs confirmed?"
- "what should we clarify next?"

No firmware or test code should be generated in the first shell-creation step.

## Worked Example Metadata

Example `project.yaml`:

```yaml
project_id: stm32f411_first_example
project_name: STM32F411 first example project
project_type: user_project
user_goal: Create a first example project for a board using stm32f411ceu6
target_mcu: stm32f411ceu6
closest_mature_ael_path: stm32f411ceu6
status: shell_created
confirmed_facts:
  - User has a board using stm32f411ceu6
assumptions:
  - The user board is close enough to the current mature stm32f411ceu6 AEL path to reuse methodology and likely implementation starting points
unresolved_items:
  - Exact board/module variant if it differs from the current mature path
  - Actual wiring/setup to be used
  - What first example the user wants to generate
current_blocker: ""
last_action: created_project_shell
next_recommended_action: clarify setup, wiring, validation approach, and desired first example
key_refs:
  - projects/stm32f411_first_example/README.md
  - docs/specs/stm32f411ceu6_bringup_preparation_v0_1.md
  - docs/specs/stm32f411ceu6_connection_contract_draft_v0_1.md
  - docs/specs/stm32f411ceu6_capability_anchor_status_v0_1.md
```

## First Natural User Questions After Creation

### 1. What did you create for me?

Answer should include:

- project shell created
- target MCU/path
- files created
- current status

Primary authority:

- project-local `project.yaml`
- project-local `README.md`

### 2. What mature AEL path is this project based on?

Answer should include:

- the selected mature path
- what is already validated there
- what can likely be reused

Primary authority:

- `project.yaml`
- current capability anchor status note

### 3. What is assumed versus confirmed right now?

Answer should include:

- confirmed facts
- assumptions
- unresolved items

Primary authority:

- `project.yaml`
- `session_notes.md`

### 4. What should we clarify before generating code?

Answer should include:

- exact setup/wiring questions
- validation approach questions
- desired example intent
- best next question to ask

Primary authority:

- `project.yaml`
- `README.md`
- setup/bring-up docs for the mature path

### 5. What first example should we generate?

Answer should include:

- ranked candidate first examples
- why one is safest first
- what setup is needed for each

Primary authority:

- mature board capability status
- current setup/connection docs

## Authority Sources

### Project-local authorities

- `projects/<project_id>/project.yaml`
- `projects/<project_id>/README.md`
- `projects/<project_id>/session_notes.md`

### System authorities for the worked example

- `python3 -m ael inventory list`
- `python3 -m ael inventory describe-test`
- `docs/specs/stm32f411ceu6_capability_anchor_status_v0_1.md`
- `docs/specs/stm32f411ceu6_bringup_preparation_v0_1.md`
- `docs/specs/stm32f411ceu6_connection_contract_draft_v0_1.md`
- `docs/current_validated_capabilities.md`

## Relationship To Existing AEL Objects

### Default verification

`default verification` remains a system-owned baseline object.

The user project should not replace it.
It may reference it as context:

- whether the mature board path is already represented in default verification
- whether a representative baseline path already exists

### Board/capability object

The board/capability layer remains the main technical authority.

The user project should point to it, not duplicate it.

For this worked example:

- `stm32f411ceu6` capability status remains authoritative for what is mature
- the project shell is only the user-facing working context

## What To Implement Now

Implement now:

- this lightweight project-shell flow
- one small project-shell scaffold template
- one small helper to create the shell
- a small AI rule for supported-or-similar project creation

Useful later:

- project-status helper answers
- richer project-to-board linking
- unknown new-board project flow

Not needed yet:

- heavy project storage
- large project schema
- dashboard/UI design
- generalized project orchestration

## Summary

For v0.1, the first user-project creation case should be:

- shell first
- setup discussion second
- generation third

This keeps AEL lightweight, AI-first, and aligned with the mature board and
baseline structures that already exist in the repo.
