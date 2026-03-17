# AEL Interaction Paradigm Shift - Chat Summary

## Overview
This document summarizes a critical design discussion between the developer and AI regarding the AEL user interface and response behavior.

## Problem Identified
The AI agent was defaulting to a **"Repository Search Assistant"** mode rather than an **"AI-Driven Embedded Lab (AEL)"** mode.

**Symptoms of the old mode:**
- Searching for `stlink` or `f411` immediately upon user inquiry.
- Listing internal scripts (`gdb_server.sh`, `probe.sh`).
- Dumping manual shell commands instead of providing an automated execution plan.
- Assuming repo configurations match user reality without clarification.

## Proposed Solution: The AEL Response Paradigm
AEL should respond as a system that can **plan and execute** hardware-related tasks under AI control.

**The Correct Response Sequence:**
1. **System Capability**: State clearly what AEL can do for the user's specific board/instrument.
2. **Instrument Role**: Explain the role of the instrument (e.g., ST-Link as a flashing/debug interface).
3. **Execution Plan**: Describe how AEL will proceed step-by-step.
4. **Realistic Constraints**: Identify setup gaps (e.g., ST-Link cannot capture GPIO waveforms).
5. **Request to Proceed**: Ask for confirmation before acting.

## Key Decisions
- **GEMINI.md Update**: Establish foundational mandates for response routing.
- **New Policy & Routing Docs**: Create `docs/specs/ael_user_facing_response_policy_v0_1.md` and `docs/agent_index/user_question_routing_v0_1.md`.
- **Formalized Skill**: Create `skills/respond_to_board_instrument_questions.md` for prioritized behavior.
- **README Update**: Prominently feature "Natural-Language-First" usage and examples.

## Reference Examples
### Good Example: ST-Link + F411
"AEL can use ST-Link as the flashing and debug interface for your board. I plan to generate a minimal smoke test, flash it through ST-Link, and verify startup via mailbox. Since ST-Link alone cannot capture waveforms, we'll start with this debug-visible signal first. Shall I proceed?"

### Bad Example (Old Mode):
"I found `instruments/STLinkInstrument/scripts/gdb_server.sh`. Run this command to start the server, then run `ael run ...`."
