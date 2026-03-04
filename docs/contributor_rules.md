# AEL Contributor Rules

Welcome to AEL.

Before submitting any pull request, please read this document carefully.

AEL is not just a tool — it is a runtime architecture.

We must protect its structure.

---

# Rule 1 — Do Not Pollute Core

Core (orchestrator) must never:

- Detect board names
- Branch on tool names
- Contain hardware heuristics
- Hardcode reset sequences

If your change requires:

```python
if "esp32" in board_name:

Stop. Redesign it.

Board-specific behavior belongs in profiles.
Rule 2 — Strategy Must Be Declarative

If you are adding:

    Reset logic

    Recovery logic

    Special timing

    Workarounds

It must be controlled by configuration fields.

Example:

reset_strategy: rts

Never hardcode behavior in adapters.
Rule 3 — Every New Experience Must Become Data

If you discovered:

    A board requires extra delay

    A tool requires retry

    A boot mode must be detected

Convert it into:

    Detectable signal

    Configurable strategy

    Structured artifact output

Never bury it in hidden logic.
Rule 4 — Adapters Are Pure Executors

Adapters:

    Execute capabilities

    Return structured results

    Do not guess context

    Do not read global state

Adapters must remain swappable and testable.
Rule 5 — Profiles Are the Knowledge Layer

All board knowledge goes into profiles:

    Tool selection

    Reset strategy

    Port configuration

    Capability mapping

Profiles are declarative.

Profiles must not execute code.
Rule 6 — All Failures Must Be Structured

Every failure must produce:

    error_summary

    error_type (if defined)

    artifacts

    recovery metadata (if attempted)

Never return raw strings only.
Rule 7 — Golden Tests Are Mandatory

Any structural change must pass:

    At least one golden test

    Python compilation

    CLI sanity check

If a change breaks golden tests, it is not acceptable.
Rule 8 — Think Runtime, Not Script

AEL is not:

    A build script

    A flashing helper

    A test runner

AEL is:

A reproducible embedded runtime verification platform.

Every contribution must strengthen that model.
Final Principle

When in doubt, ask:

Does this change increase structural clarity?

Or does it introduce special-case knowledge?

If it introduces special-case knowledge, redesign.

We are building infrastructure, not patches.

Future PRs may be rejected if they violate architectural boundaries.
