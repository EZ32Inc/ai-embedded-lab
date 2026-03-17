# AEL Project Lifecycle v0.1

## Purpose
This document defines the lifecycle of a **User Project** in AEL. It governs how the agent should guide the user from an initial hardware bring-up request to a fully validated and closed-out experiment.

## The Five Stages of AEL Project Lifecycle

### 1. Intake (Reality Clarification)
- **Goal**: Confirm the user's actual physical hardware setup (Bench) and map it to repo references.
- **Agent Action**: 
  - Detect the board and instrument.
  - Call `python3 -m ael project intake` (conceptually) to resolve the "Known vs Assumed vs Needed" gap.
  - Output confirmed facts to `projects/<id>/project.yaml`.
- **Command**: `python3 -m ael project create --target-mcu <mcu>`

### 2. Plan (Strategic Design)
- **Goal**: Define a sequence of safe experiments (Plans) to move from "Unknown" to "Validated".
- **Agent Action**: 
  - Propose a "Step 0" smoke test (usually Mailbox-based).
  - Define the capture/stimulus wiring requirements.
  - Wait for user confirmation of the plan.

### 3. Execute (Automated Loop)
- **Goal**: Run the BUILD -> FLASH -> RUN -> VERIFY pipeline.
- **Agent Action**: 
  - Execute `python3 -m ael run <plan.json>`.
  - Capture evidence (logs, signals, results).
  - Link the result to the project: `python3 -m ael project link-run --run-id <run_id>`.

### 4. Review & Adapt (Evidence Interpretation)
- **Goal**: Analyze PASS/FAIL evidence and decide on the next step.
- **Agent Action**: 
  - If **PASS**: Mark the capability as `validated`.
  - If **FAIL**: Diagnose (Connection Doctor, Log analysis), propose a fix, and loop back to Execute.
- **Command**: `python3 -m ael project status <id>` to check blocker state.

### 5. Closeout (Knowledge Persistence)
- **Goal**: Record the final validated state and archive session notes.
- **Agent Action**: 
  - Update `session_notes.md` with key learnings (e.g., "USART2 PD5/PD6 required on F407").
  - Finalize the `project.yaml` status.

---

## Workflow Memory Files
Each project is stored in its own directory:
- `projects/<id>/project.yaml`: Current state, blockers, and capability markers.
- `projects/<id>/session_notes.md`: Qualitative log of the bring-up process.
- `projects/<id>/confirmed_facts.json`: Persistent physical wiring/setup truth.
