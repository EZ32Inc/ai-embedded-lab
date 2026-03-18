# AEL Domain Response Contract v0.1

## Purpose

This document defines the required structure for AI responses when a user makes
a board + testing request (e.g. "I want to test STM32H743 with ESP32JTAG").

The AI MUST organize its response using the four sections below. This makes the
system domain / user project domain / branch concept visible to the user, not
just stored internally.

---

## Required Response Structure

### Section 1 — System Domain

State the current AEL system main status for the requested MCU:

- Is the MCU present in system main (`assets_golden/`)? → **copy hit**
- Is there a close family reference but not an exact match? → **copy miss / inferred**
- No reference at all? → **copy miss / unknown**

If inferred, name the reference DUT and its `lifecycle_stage`.

Example:
```
## System Domain
- STM32H743: NOT in system main (assets_golden/) — copy miss
- Closest reference: stm32h750vbt6 (H7 family, merged_to_main, fully verified)
- Path maturity: inferred (confidence: medium)
```

### Section 2 — User Project Domain

Describe what will be created for the user:

- `project_id` to be created
- `domain: user_project_domain`
- `capability_source: main | branch`

Example:
```
## User Project Domain
- Project: stm32h743_bringup
- domain: user_project_domain
- capability_source: branch  (H743 not in system main; branch capability will be created)
```

### Section 3 — Branch Capability (only when capability_source == branch)

Make the branch lifecycle explicit:

- Location: `assets_branch/duts/{id}/`
- Initial `lifecycle_stage: draft`
- Full lifecycle path

Example:
```
## Branch Capability
- assets_branch/duts/stm32h743_draft/
- lifecycle_stage: draft
- Lifecycle path: draft → runnable → validated → merge_candidate → [ael dut promote] → merged_to_main
- Commands:
    ael dut show-placeholders --id stm32h743_draft
    ael dut set-lifecycle --id stm32h743_draft --stage runnable
    ael dut promote --id stm32h743_draft
```

### Section 4 — Cross-Domain Link

State the connection between this user project and the system domain:

- What the user project can contribute back to system main
- The promote path

Example:
```
## Cross-Domain Link
- If stm32h743_bringup validates successfully → stm32h743_draft becomes a promote candidate
- Promote path: ael dut promote --id stm32h743_draft → enters assets_golden/ as merged_to_main
- This user project drives H7-family expansion in system main
```

---

## When This Contract Applies

Apply this structure when the user request involves:

- Requesting tests on a specific MCU/board
- Asking to create a new project
- Asking "what would happen if I want to test X?"
- Any response that involves `project create` or capability creation

---

## When This Contract Does NOT Apply

Do not apply this structure for:

- Simple command help questions
- Single-step clarifications
- Instrument or connection questions not involving project creation

---

## Relationship to Other Policies

This contract extends:
- `confirm_before_generation_policy_v0_1.md` — the Full Plan structure gains domain/branch sections
- `known_board_clarify_first_policy_v0_1.md` — clarify-first still required; domain framing wraps it
- `ael_user_facing_response_policy_v0_1.md` — Five-Step Rule is still followed within each section

The domain response structure is the outer container. The existing policies apply
within Section 2 (User Project Domain) for clarification and confirmation steps.
