# AEL AI Usage Rules

## CLI is for AI, not for humans

In AEL, the CLI is primarily a machine interface.

Humans are expected to interact with AEL through:

- AI agents (e.g. Codex)
- Web UI
- Messaging interfaces (e.g. Discord)

The CLI exists as a deterministic control layer for AI to drive the system.

Think of CLI as:

Control Language Interface

not

Command Line Interface.

---

## Design Principle

When adding or modifying CLI features, optimize for:

- machine usability
- determinism
- composability
- reproducibility

Do NOT optimize for:

- human typing convenience
- memorability
- UX friendliness

Example:

Adding `--dut` is valuable because it allows AI to select hardware intent precisely.

It is not intended for manual use.

---

## Role of CLI

CLI serves as:

- AI control plane
- debugging interface
- reproducibility tool

It is NOT the primary user interface.

---

## Primary UX Model

Human → AI → CLI/API → AEL → Instruments → DUTs

Humans express intent in natural language.

AI translates that intent into structured execution.

CLI executes those structured instructions.

---

## Implementation Guidance

When implementing features:

- Expose structured parameters (e.g. `--dut`, `--bench`)
- Avoid interactive prompts
- Prefer explicit inputs over implicit guessing
- Ensure runs are replayable via CLI

This allows AI to:

- generate execution plans
- reason about failures
- retry deterministically

---

## Future Direction

CLI will eventually be complemented by:

- Job API
- Web interface
- Messaging integrations

But CLI remains the stable execution layer.

---

## Summary

Design CLI for AI consumption, not human usage.

## Inventory Questions

For DUT, MCU, and test-coverage questions, prefer the repo-native inventory command first:

- `python3 -m ael inventory list`
- `python3 -m ael inventory list --format text`

For detailed per-test questions such as connections, expected checks, or what a test will do, prefer:

- `python3 -m ael inventory describe-test --board <board_id> --test <test_path>`
- `python3 -m ael inventory describe-test --board <board_id> --test <test_path> --format text`

Use manual repo inspection only as fallback when the inventory command is missing or insufficient.

For connection questions specifically, answer in this order:

1. resolved `inventory describe-test`
2. test plan
3. board profile
4. firmware source only to identify missing contract data

Separate:

- formal contract
- inferred implementation detail
- missing contract data

## DUT Instance Disambiguation

When adding a new test for a board family that already exists in AEL, do not assume it uses the existing DUT automatically.

First classify it explicitly as one of:

- `same_dut_instance`
- `independent_dut_instance`

Ask or confirm:

1. Is this new test using the same physical DUT instance as the existing tests, or a separate physical DUT instance?
2. If it is the same DUT instance, does it require a different setup state, wiring state, or dedicated instrument assignment?
3. If it is a separate DUT instance, what is the new DUT instance id?

Rules:

- Same board family does not imply same DUT instance.
- Same DUT instance should remain serialized through the existing `dut:<id>` resource lock.
- Independent DUT instances should get distinct board ids and board configs.

## First-Time MCU Support

When extending AEL to a brand-new MCU or board that AEL has not previously
supported, do not treat existing repo code as the primary implementation basis.

First separate:

- peripheral implementation source
- test methodology source

Rules:

1. Peripheral implementation must be anchored first in official vendor sources.
   This includes:
   - datasheet
   - reference manual
   - official SDK/CMSIS support
   - official startup/system files
   - official vendor examples
2. Previously validated AEL tests should be reused primarily for methodology:
   - validation structure
   - staged flow
   - banner/proof patterns
   - connection strategy
3. Do not copy old MCU code blindly.
4. Do not assume register-level implementation details are portable across MCU
   lines.
5. Before generation, explicitly call out:
   - confirmed facts
   - inferred assumptions
   - unresolved drift
   - official sources selected
   - AEL methodology sources selected
6. After each meaningful round, record:
   - what succeeded
   - what failed
   - what was inferred
   - what was learned
7. After a first-pass new-board suite becomes stable, do the closeout
   validations explicitly:
   - rerun the cleaned full board suite on live hardware
   - decide whether one representative DUT-backed test should enter default
     verification
   - if you add that test to default verification, prove it by running the live
     default-verification flow
8. Prefer the representative default-verification candidate to be the lowest-risk
   validated baseline for that board, usually the board-specific
   `gpio_signature`-style test, not the whole new suite.

## User Project Creation For Supported Boards

When the user asks to create a first project for a board that is already
supported by AEL, or is highly similar to a mature supported path, do not jump
straight into code generation.

For v0.1, do this instead:

1. create a lightweight empty-shell user project
2. record the user goal
3. resolve the closest mature existing board/capability path
4. record:
   - confirmed facts
   - assumptions
   - unresolved items
5. present the best next setup/validation questions
6. only after setup and intent are clarified should code generation be proposed

Rules:

- treat the project shell as a lightweight user-facing context layer
- keep `default verification` as a system-owned baseline object
- keep board/capability notes as the technical authority
- record lightweight cross-domain links when the project is anchored to current system capabilities
- do not design a heavy project-management system for this v0.1 case

If branch-specific AEL tool changes matter to the project, record them lightly:

- `tool_branch`
- `system_change_status`

Do not introduce a broad branch-tracking subsystem for this v0.1 flow.

Worked example:

- user says: "I have a board using `stm32f411ceu6`. Please create a first
  example project for me."
- the first response should create the project shell and anchor it to the
  mature `stm32f411ceu6` path
- it should not generate firmware immediately unless the user explicitly asks
  to skip setup clarification


## Stage Questions

For questions about what `plan`, `pre-flight`, `run`, or `check` include, prefer the repo-native stage explanation command first:

- `python3 -m ael explain-stage --board <board_id> --test <test_path> --stage <stage>`
- `python3 -m ael explain-stage --board <board_id> --test <test_path> --stage <stage> --format text`

Use manual code inspection only as fallback when the stage explanation command is missing or insufficient.

## Default Verification Repeat Requests

When interpreting repeated default-verification requests, use worker-level repeat as the default operational meaning.

- If the user asks to run default verification `N` times, use:
  - `python3 -m ael verify-default repeat --limit N`
- Do not use an outer shell loop around `python3 -m ael verify-default run` unless the user explicitly asks for suite-round serialization.
- Treat outer shell loops as a special case for round-by-round suite pacing, not the normal repeated baseline behavior.

## Live Bench Execution

Commands that touch live bench resources must be run with escalated permissions
from the start.

This includes commands that access:

- real instrument endpoints
- DUT network endpoints
- probe APIs
- serial bridge daemons
- hardware verification flows

Examples:

- `python3 -m ael verify-default run`
- `python3 -m ael verify-default repeat --limit N`
- `python3 -m ael run --board <board_id> --test <test_path>`
- live bridge/probe smoke commands against real bench endpoints

Rules:

1. Do not perform sandbox trial runs first for live-bench commands.
2. If a sandboxed live-bench command fails due to network restriction or bench
   access policy, classify it as `INVALID`, not `FAIL`.
3. `INVALID` means the command did not have valid bench access and no hardware
   conclusion is allowed.
4. Only bench-reachable runs should be used for DUT, probe, instrument, or
   suite health judgments.

## New Board Closeout Rule

When a brand-new board has reached first-pass validation and cleanup is being
finalized, do not stop at "the individual tests passed once."

Required closeout sequence:

1. Remove or isolate temporary diagnostics used only for bring-up.
2. Rerun the cleaned full board suite on live hardware.
3. Register the board as a DUT in inventory if it is intended to be a normal
   AEL DUT.
4. Decide whether a representative DUT-backed baseline test should be added to
   default verification.
5. If added, run live default verification to prove that the new step resolves,
   executes, and reports correctly inside the existing baseline flow.

Rationale:

- This catches cleanup regressions that are easy to miss if only ad hoc single
  tests were used during bring-up.
- It proves the board is integrated into AEL as a DUT, not only as a local
  experimental path.
- It keeps default verification anchored to one representative low-risk DUT test
  per new board rather than expanding to the whole board suite by default.

Interpretation:

- `PASS`: the real bench was reached and validation succeeded.
- `FAIL`: the real bench was reached and validation failed.
- `INVALID`: the real bench was not actually reached.
