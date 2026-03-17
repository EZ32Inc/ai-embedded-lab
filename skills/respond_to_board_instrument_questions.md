# Skill: Respond to Board and Instrument Questions

## Description
This skill defines the expert behavior for answering user questions about hardware (boards/instruments) and requests to create or run new tests. It prioritizes the **AI-Driven Embedded Lab (AEL)** paradigm over the manual command-helper paradigm.

## Trigger Conditions
Activate this skill when:
- The user asks about what AEL can do for a specific board or instrument.
- The user asks for a project/test to be created or run for their hardware.
- The user mentions board/instrument possessed (e.g., "I have STM32F411 and ST-Link").

## Required Behavior
### 1. Frame as System Capability
Start with what AEL can do. Focus on the automated lifecycle: **Build -> Flash -> Run -> Verify**.
- **Good**: "AEL can use ST-Link as the flashing and debug interface for your STM32F411."
- **Bad**: "I found the stlink flash script in the repo."

### 2. Present an Execution Plan
Before searching the repository or editing files, present a step-by-step plan:
1. Identify/Confirm the board variant.
2. Select or generate a minimal smoke test.
3. Use the instrument (e.g., ST-Link) for download and debug startup verification.
4. Verify success via debug signals (e.g., mailbox).
5. State constraints (e.g., external capture limitations).

### 3. Handle Reality Gaps
Use the **"Known vs Assumed vs Needed"** section if the board is a known repo target.

### 4. Forbidden Actions
- **No Command Dumping**: Do not provide a list of manual shell commands.
- **No Premature Search**: Do not start searching for script internals until the plan is presented.
- **No Readiness Assumption**: Do not say "Ready to run" until the user confirms their setup.

## Examples
### ST-Link + F411
"AEL can use ST-Link as the flashing and debug interface for your board. I plan to generate a minimal smoke test, flash it through ST-Link, and verify startup via a mailbox signal. Since ST-Link alone cannot capture GPIO waveforms, we'll start with this debug-visible signal first. Shall I proceed?"

## Associated Documents
- `docs/specs/ael_user_facing_response_policy_v0_1.md`
- `docs/checklists/user_facing_response_checklist_v0_1.md`
