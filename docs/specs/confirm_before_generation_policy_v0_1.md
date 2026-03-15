# Confirm-Before-Generation Policy v0.1

## Purpose

This policy defines a required interaction contract: AEL must not immediately
perform generation or repository-changing actions after interpreting a user
request. Instead, it must first produce a structured execution plan and obtain
explicit user confirmation before proceeding.

The goal is to prevent silent assumptions, premature file creation, and
irreversible actions taken on incomplete information.

---

## The Core Rule

**User request → Plan generation → User confirmation → Execution**

No action listed in the scope below may be executed in the same response turn
in which the request is interpreted.

The plan must be presented as a distinct step. The user must explicitly
acknowledge or approve the plan before any action is taken.

---

## Scope — When This Policy Applies

This policy applies to any action that:

- creates, modifies, or deletes files in the repository
- creates or modifies a project record (`project.yaml`)
- generates test code, firmware, or configuration
- promotes a DUT, project, or example through a lifecycle stage
- defines or modifies a DUT entry
- initiates or schedules a hardware verification run

Specifically, the policy applies to — but is not limited to — the following
operation types:

| Operation | Plan type required |
|---|---|
| New project creation | Full plan |
| New board bootstrap | Full plan |
| New DUT definition | Full plan |
| Lifecycle promotion | Full plan |
| New verification capability definition | Full plan |
| Test generation for existing project | Full plan |
| Add test to existing project | Lightweight plan |
| Add note or confirmed fact to project | Lightweight plan |
| Repository config modification | Full plan |
| Hardware verification run | Full plan |

---

## Execution Plan Structure

### Full Plan

Used for high-impact operations. Must contain all eight fields.

```
Goal
  What the user wants to accomplish, as understood by the system.

Detected Context
  Board name, project ID, MCU family, instrument, and repository
  references detected from the user request and system state.
  State whether each item comes from: user statement, project record,
  repository inventory, or system inference.

Planned Actions
  Numbered list of operations the system will perform, in order.
  Each action must be specific enough that the user can predict the result.

Assumptions
  Facts the system is treating as true that were not explicitly confirmed
  by the user in this session.
  Each assumption must be labeled with its source:
    - [repo] — from repository config, inventory, or known_boards.yaml
    - [inferred] — derived from partial information
    - [prior session] — from a previous confirmed_facts entry

Information Still Needed
  Facts that must be confirmed by the user before execution can proceed.
  If this list is empty, state: "No additional information required."

Expected Outputs
  Files, records, or configurations that will be created or modified.
  Include: file path, type, and what it represents.

Boundaries / Risks
  What the system cannot guarantee at this stage.
  Must always include physical-reality boundaries:
    - AEL cannot confirm physical wiring or connections.
    - AEL cannot verify that hardware is powered and connected.
    - Repository references are starting points, not confirmed user setup.

Confirmation Prompt
  Explicit request for user approval before any action is taken.
  Standard wording: "Does this plan look correct? Confirm to proceed,
  or let me know what to change."
```

### Lightweight Plan

Used for small, low-impact operations on existing projects.

Must contain:

```
Goal
  One sentence stating what will be done.

Planned Actions
  Short list of what will change.

Key Assumptions
  Any repo or inferred facts being used.

Confirmation Prompt
  Explicit request for approval before proceeding.
```

A lightweight plan may omit: Detected Context, Information Still Needed,
Expected Outputs, and Boundaries / Risks — **only if** the operation is
additive, does not create new files, and affects only an existing confirmed
project record.

---

## Workflow Detail

### Step 1 — Request Interpretation

The system reads the user request and determines:

- What operation type is being requested
- Which plan type is required (full or lightweight)
- What context can be detected (board, project, instrument, intent)
- What is missing

The system must NOT perform any file writes, CLI executions, or state changes
during this step.

### Step 2 — Plan Generation

The system produces the plan document using the structure above.

The plan is presented to the user in full before any action is taken.

During plan generation, the system may run read-only commands:
- `python3 -m ael project list`
- `python3 -m ael project status <id>`
- `python3 -m ael inventory list`

Read-only operations that do not modify state are permitted during planning.

### Step 3 — User Confirmation

The user must respond with an explicit approval such as:
- "yes", "confirmed", "go", "proceed", "looks good"
- Or a correction that updates the plan

Silence or ambiguity is not confirmation. If the user's response is unclear,
the system must ask before proceeding.

### Step 4 — Execution

After confirmation, the system executes the planned actions in order.

If an action fails, the system must stop and report the failure before
attempting subsequent actions.

The system must not silently skip failed actions or substitute alternatives
without reporting the substitution.

---

## What Counts As A Plan

A plan is sufficient when:

- every planned action is described specifically enough for the user to
  predict the result
- all assumptions are labeled with their source
- physical-reality boundaries are stated
- a confirmation prompt is present

A plan is NOT sufficient when:

- it says only "I will create the project" without listing what files
  and records will be created
- it omits assumptions that were not stated by the user
- it presents repository reference data as if already confirmed by the user
- no explicit confirmation is requested

---

## Wording Rules

Use this kind of wording in plans:

- "I plan to create `projects/stm32f411_first_example/project.yaml`."
- "Assumption [repo]: instrument is esp32jtag — please confirm this matches your setup."
- "This will modify the lifecycle state of DUT `stm32f411_gpio_dut_001`."
- "Boundary: AEL cannot verify that your board is physically connected."
- "Confirm to proceed, or let me know what to change."

Do NOT use:

- "I'll go ahead and create the project." (no plan, immediate execution)
- "Since you mentioned STM32F411, I've created the project." (executed without confirmation)
- "Your board is ready." (physical-reality claim without user confirmation)
- "Using esp32jtag at 192.168.2.103." (presenting repo data as confirmed user fact)

---

## Relationship To Adjacent Policies

- `known_board_clarify_first_policy_v0_1.md`: that policy requires confirmation
  of board, instrument, wiring, and intent before treating a path as ready.
  This policy adds the requirement that execution itself must be preceded by
  a plan stage, even after clarification is complete.
- `ael_orientation_skill.md`: the orientation skill must inform the user that
  execution actions will produce a plan before running. The orientation layer
  is a discovery step, not an execution step — it is exempt from plan
  requirements for read-only context gathering.
- `user_project_creation_skill.md`: project creation is subject to this policy.
  The creation workflow must produce a full plan before writing any files.
- `dut_promote` command: lifecycle promotions are in scope. A promotion plan
  must be shown before the promotion is executed.

---

## Exemptions

The following actions are exempt from this policy and may proceed without a
prior plan step:

- Read-only commands: `project list`, `project status`, `inventory list`,
  `project answering-context`
- Responses to factual questions about the system, repository, or policy
- Orientation responses (context A, B, C, D) that do not involve execution
- Re-displaying a previously confirmed plan that was interrupted

---

## Design Intent

This policy exists because:

1. Repository actions taken on incomplete information create artifacts that
   must be manually cleaned up.
2. Users cannot verify correctness of an action they did not see described
   before it ran.
3. Physical-reality boundaries — wiring, connections, hardware power — can
   never be confirmed by the system. Execution without explicit user
   acknowledgment of these boundaries is unsafe for hardware validation work.
4. Structured plans create a shared mental model between user and system
   before any irreversible work begins.

The goal is not to slow down interaction. Lightweight plans for small
operations are intentionally short. The goal is to ensure the user always
knows what is about to happen before it happens.
