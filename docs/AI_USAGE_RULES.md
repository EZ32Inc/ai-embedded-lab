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

Interpretation:

- `PASS`: the real bench was reached and validation succeeded.
- `FAIL`: the real bench was reached and validation failed.
- `INVALID`: the real bench was not actually reached.
