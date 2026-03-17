# User Question Routing v0.1

## Purpose
This document provides short routing guidance for user-facing AEL responses. It helps the agent classify user questions and select the correct answering mode.

## Trigger Conditions
Consult this document if the user asks questions like:
- What can AEL do?
- How do I use ST-Link (or any instrument) with this project?
- Can AEL test my board (or any board)?
- I have board X and instrument Y, can you run a test?
- Can you generate and flash a test for me?
- Can AEL debug/program/verify my board?

## Routing Step
1. **Identify the Inquiry Category**: Capability, Board/Instrument Usage, or Execution Request.
2. **Action**: Load `docs/specs/ael_user_facing_response_policy_v0_1.md` and activate `skills/respond_to_board_instrument_questions.md`.
3. **Constraint**: Do not begin with repository search or command dumps.

## Short Routing Rule
- If the question is about **what AEL can do** or **how to use AEL** for hardware tasks:
  - **Path**: Product Capability + Execution Plan
  - **Mode**: User-facing AEL
- If the question is about **manual shell commands**:
  - **Path**: Command Help
  - **Mode**: Documentation Assistant (Manual Steps)

---

## Priority Reference
`docs/specs/ael_user_facing_response_policy_v0_1.md`
