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
