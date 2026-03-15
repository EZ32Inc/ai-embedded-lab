# User Project Creation Skill

## Purpose

This skill defines the lightweight v0.1 behavior for creating a user project in
AEL when the target board is already supported, or is highly similar to an
existing mature path.

Its first concrete worked example is:

- `stm32f411ceu6`

## Core Rules

### Rule 1: No immediate code generation

Do not jump straight into code generation when the user says:

> "Please create a first example project for me."

For v0.1, do this instead:

1. create a lightweight empty-shell project
2. record the user goal
3. resolve the closest mature AEL board/capability path
4. record a lightweight user association using `project_user`
5. record confirmed facts, assumptions, and unresolved items
6. record lightweight cross-domain links to the mature system path
7. present the best next setup/validation questions
8. only after that discuss generation, build, flash, and verify

### Rule 2: Known-board clarify-first (critical)

Even when a known mature repo path exists, do NOT treat it as proof that
the user's real setup matches that path.

A known repo path is a candidate reference, not a confirmed user setup.

When identifying a candidate repo path, immediately output:

- what was found in the repo (board config, instrument, test plan, wiring)
- what is assumed but not yet confirmed about the user's real setup
- what the user must still provide before the path can be treated as runnable
- what the next step is

This applies even if the candidate path is a strong match.

For the full policy, required confirmation checklist, wording rules, and
response structure, see:
`docs/specs/known_board_clarify_first_policy_v0_1.md`

## Trigger / When To Use

Use this skill when:

- the user asks to create a first project for a supported board
- the user asks to start work around an already mature board family
- the user needs project-local context before setup/generation work begins

Do not use this skill as the primary workflow for:

- first-time unsupported MCU bring-up
- broad project-management features
- final code generation in the first response

## Required Outputs

At minimum, this skill should produce:

- project folder path
- `project.yaml`
- `README.md`
- `session_notes.md`
- selected mature board/capability anchor
- domain marker showing this is user-project work
- lightweight `project_user` association
- lightweight cross-domain links to the system domain
- confirmed facts
- assumptions
- unresolved items
- best next questions

## Current Worked Example

For:

> "I have a board using stm32f411ceu6. Please create a first example project for me."

The skill should:

- create a shell under `projects/`
- anchor to the mature `stm32f411ceu6` path as a **candidate reference**
- point to current F411 setup/capability docs
- avoid generating code until setup and first-example intent are clarified
- immediately output a structured missing-info block:

```
A. Known from repo:
   Candidate path: stm32f411ceu6
   Candidate instrument: esp32jtag (from repo config)
   Candidate test: stm32f411_gpio_signature
   Candidate wiring: PA2→P0.0, PA3→P0.1, SWD→P3, GND→probe GND

B. Assumed but not confirmed:
   - board variant matches WeAct Black Pill V2.0
   - instrument matches or is compatible with esp32jtag
   - wiring matches repo bench_setup
   - intended first test is GPIO toggle / LED blink

C. Still needed from you:
   - Which exact board variant do you have?
   - What instrument are you using for debug/flash?
   - Is your wiring the same as the repo setup, or different?
   - What should the first test demonstrate?

D. Next step:
   Confirm or correct the above, then I can prepare a runnable path
   for your real setup.
```

The skill should NOT say:

> "Your project is ready. Using esp32jtag. Wiring confirmed. Ready to flash."

unless the user has explicitly confirmed those facts.

## Partial-Match Handling (Critical)

When the user confirms some setup details but not others — especially when the
instrument differs from the repo reference — apply the five-component evaluation:

**A.** Target board/variant (MCU, pin layout) — can confirm independently
**B.** Functional intent (what test/experiment) — confirm independently
**C.** Flash/debug instrument — if different from repo, bench wiring differs too
**D.** Capture/verification path — instrument-dependent; ST-Link cannot capture GPIO
**E.** Full bench setup — only confirmed if instrument matches AND wiring is confirmed

### Example: User Has ST-Link (Repo Reference: esp32jtag)

User says: "WeAct Black Pill / ST-Link / Yes to wiring / Yes to LED blink."

Do NOT collapse this into "wiring confirmed":

- ✓ Board variant: confirmed (A)
- ✓ Functional intent: LED blink confirmed (B)
- ✗ Instrument mismatch: ST-Link ≠ esp32jtag (C) — bench wiring differs
- ✗ Capture path: not established (D) — ST-Link has no GPIO capture
- ✗ Full bench setup: NOT confirmed (E) — "Yes to wiring" only confirms MCU-side pin intent

Required output when instrument differs:

```
Partial match found:
  Target board/variant:     ✓ confirmed (WeAct Black Pill)
  Functional intent:        ✓ confirmed (LED blink)
  Instrument:               ✗ mismatch — you stated ST-Link, repo uses esp32jtag
  Target-side wiring:       ✓ likely carries over (LED at PC13, GPIO at PA2/PA3 unchanged)
  Instrument-side wiring:   ✗ NOT confirmed — repo wiring (PA2→P0.0, SWD→P3) is esp32jtag-specific

Still needed:
  - Your ST-Link to STM32 SWD wiring (SWDIO, SWDCLK, GND, NRST)
  - How will GPIO signals be captured/verified? (ST-Link cannot capture without extra hardware)
  - Note: the stm32f411_gpio_signature test requires GPIO capture — may need different test or instrument
```

This is captured in:
`docs/specs/known_board_clarify_first_policy_v0_1.md` — Partial-Match Evaluation section

## Option B — External Bench Execution Path

When the user's instrument is user-local (not reachable from the AEL machine),
the execution path switches to **Mode B: External Bench**.

This happens automatically when:
- Instrument mismatch is confirmed (e.g., user has ST-Link, repo uses esp32jtag)
- `run-gate` returns `blocked` due to instrument mismatch
- The user's instrument is not in `configs/instrument_instances/`

### Mode B Response Contract (stops at build + instructions)

The assistant MUST:
1. Build the firmware locally — report success/failure and artifact path
2. Provide the user-side flash command for their instrument
3. Provide verification instructions (visual, oscilloscope, etc.)
4. Stop — do NOT attempt to run flash/debug tools against user's instrument

The assistant must NOT:
- Run `openocd`, `st-flash`, `JLinkExe`, or similar against hardware not attached here
- Report "flash succeeded" without an actual AEL-reachable instrument run
- Imply local build success = local hardware access

### Example: STM32F411 + ST-Link + Visual Verification

After confirming: WeAct Black Pill / ST-Link / LED at PC13 / visual observation

Correct response:

```
Build: success
Artifact: firmware/targets/stm32f411ceu6/build/stm32f411_app.bin (980 bytes)

Flash on your bench (ST-Link):
  st-flash write stm32f411_app.bin 0x08000000
  # or with OpenOCD:
  openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
          -c "program stm32f411_app.bin 0x08000000 verify reset exit"

Verify: LED at PC13 should blink ~1 Hz. Verify by visual observation.

AEL machine-verified run: not available (ST-Link is user-local, not reachable here).
```

Not acceptable:
```
Running openocd... [attempts local flash against user's ST-Link]
```

Full policy: `docs/specs/external_bench_execution_boundary_v0_1.md`

## Relationship To Existing AEL Objects

- `default verification` remains a system-owned baseline object
- board/capability notes remain the technical authority
- the user project is only a lightweight user-facing working context
- branch-specific tool variants may be recorded lightly as project metadata when relevant, but do not require a new subsystem
- collaboration remains Git-based in v0.1, not account-based

## Summary

For v0.1, user-project creation should be:

- shell first
- setup discussion second
- generation third
