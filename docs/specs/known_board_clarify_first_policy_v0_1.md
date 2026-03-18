# Known-Board Clarify-First Policy v0.1

## Purpose

This policy defines the required assistant behavior when a user requests a project
or experiment for a board that already has a known mature path in the AEL repo.

It fills a specific gap: the system previously mapped a known board name to a repo
path and responded with high confidence as if the user's real board, instrument,
wiring, and intended experiment were already confirmed. That behavior is not
reliable enough for real-world engineering use.

## The Core Rule

A known repo path is a candidate reference, not proof that the user's real setup matches.

The system MUST distinguish between:

1. **Repo-known**: a board config, instrument profile, test plan, and wiring
   description exist in the AEL repo for this MCU/board family.
2. **User-confirmed**: the user's actual physical board, instrument, connections,
   and intended experiment have been explicitly confirmed for this session.

The system may identify a candidate repo path freely.
The system must NOT state or imply that the user's setup is ready to run
until the real-world facts in the confirmation checklist have been provided.

## When This Policy Applies

This policy applies whenever:

- the user asks to create a project for a board that matches a known AEL path
- the user asks to generate an experiment or first example for a known MCU/board
- the system resolves a user request to a mature board path in the inventory

It does NOT apply to:

- unsupported or unknown boards (see separate unknown-path policy)
- requests that explicitly state the user's setup matches the repo reference
- follow-up requests where the confirmation checklist has already been completed

## Confirmation Checklist

For known-board requests, the following must be confirmed before treating any path
as "ready to run" for the user's real setup:

| Item | Required confirmation |
|---|---|
| Board identity | exact board name or variant the user has |
| MCU identity | exact MCU (relevant when family has multiple variants) |
| Instrument | what debug/flash/measurement instrument the user plans to use |
| Connections | how the board is wired to the instrument and bench |
| Intended first test | what the user wants to validate or demonstrate first |
| Readiness intent | does the user want to reuse the repo path as-is, or adapt for their real setup? |

A candidate path match satisfies none of these items on its own.

Repo facts — board config, instrument profile, test plan, bench_setup — are
reference starting points, not confirmed user facts, unless the user explicitly
confirms them.

## Readiness States For Known-Board Requests

Use these states to describe where a known-board request currently stands:

### `candidate_path_identified`

A repo path has been found that may match the user's request.
None of the confirmation checklist items have been confirmed yet.
The system should not proceed to build/flash/verify from this state.

### `partially_confirmed`

Some confirmation checklist items have been provided by the user.
The system may narrow its candidate path and prepare a more specific plan,
but should still list what remains unconfirmed.

### `confirmed_enough_to_prepare`

All or most confirmation checklist items have been provided.
The system may proceed to prepare a runnable path using the confirmed real setup.
The system should still clearly state which facts came from the repo and which
came from the user.

## Required Response Structure For Known-Board Requests

When responding to a known-board request, structure the response to clearly show:

**A. What is known from the repo**
- candidate board config found
- candidate instrument profile found
- candidate test plan found
- candidate wiring / bench_setup found

**B. What is assumed but not yet confirmed**
- whether the user's board matches the repo variant
- whether the user has the same or compatible instrument
- whether the wiring matches the repo bench_setup
- what the intended first experiment is

**C. What must still be provided by the user**
- the items from the confirmation checklist that have not yet been confirmed

**D. What the next step is**
- a concrete, safe next step the user can take
- typically: answer the confirmation questions, then the system can proceed

## Wording Rules

Use this kind of wording:

- "A known repo path exists for X — this is a candidate reference."
- "I still need to confirm your actual board / instrument / wiring."
- "The repo path uses Y as the instrument — please confirm whether this matches your setup."
- "This can be used as a starting point, but it should not yet be treated as your validated real setup."

Do NOT use this kind of wording when real setup is unconfirmed:

- "This project is ready to run."
- "Your board is validated."
- "Setup matches — ready to flash."
- "Using your instrument X." (unless the user explicitly stated X)

## Post-Plan Missing-Info Output Requirement

After a candidate path is identified or a plan-stage succeeds, the system MUST
proactively output a structured missing-info section covering:

```
Candidate repo path:   <board config / test plan used>
Assumed instrument:    <instrument profile from repo>
Assumed wiring:        <bench_setup or connection from repo>
Missing confirmations: <items from checklist not yet provided>
Next step for user:    <what the user should provide to continue>
```

This output is required even if the user did not ask for it.
The user should not have to guess what information is still needed.

## Partial-Match Evaluation

When the user's setup partially overlaps with the repo reference path — for example,
matching the board but using a different instrument — the system must evaluate each
component separately. A partial match must NOT be collapsed into a single yes/no.

### Five-Component Evaluation Model

When a known repo path is found and the user provides setup details, evaluate:

| Component | What to check | Can it carry over? |
|---|---|---|
| A. Target board / variant | MCU part number, board variant, pin layout | Yes, if user confirms exact match |
| B. Functional intent | What experiment/test the user wants to run | Yes, if test plan covers the intent |
| C. Flash/debug instrument | What instrument the user has for SWD/JTAG/USB | Only if same or compatible instrument |
| D. Capture / verification path | How GPIO signals are captured and measured | Only if instrument has capture capability |
| E. Full bench setup | Complete wiring: target-side + instrument-side | Only if instrument is the same |

### Instrument Change Invalidates Full Bench Match

If the user's instrument differs from the repo reference instrument:

- **Target-side wiring may still apply**: LED pin, GPIO pins on the MCU are instrument-independent
- **Instrument-side bench wiring does NOT apply**: probe pin mappings (P0.0, P0.1, etc.),
  SWD port, and any instrument-specific connections are instrument-specific
- The full bench setup match (component E) is NOT established
- The system must NOT treat a "Yes" answer to generic wiring questions as confirming
  instrument-side bench wiring when the instrument has changed

### Example: ST-Link Instead Of esp32jtag

Repo reference for stm32f411ceu6:
- Instrument: esp32jtag
- Bench wiring: PA2→P0.0, PA3→P0.1, SWD→P3, GND→probe GND

User says: "I have WeAct Black Pill. I use ST-Link. Yes to wiring."

Correct evaluation:
- A. Target board: ✓ confirmed (WeAct Black Pill matches)
- B. Functional intent: pending (what test?)
- C. Flash/debug instrument: ✗ mismatch — ST-Link ≠ esp32jtag
- D. Capture/verification path: ✗ not established — ST-Link has no GPIO capture capability
- E. Full bench setup: ✗ NOT confirmed — the "Yes to wiring" only covers MCU-side pin intent

Required follow-up:
- What are your ST-Link to STM32 SWD connections?
- How will you capture/verify GPIO signals? (ST-Link cannot do this without extra hardware)
- The existing `stm32f411_gpio_signature` test requires capture — it may not run with ST-Link alone

### Wording For Partial-Match Cases

When instrument differs from repo reference, say:

- "Partial match: board/variant confirmed, but instrument differs from repo reference."
- "Target-side wiring (LED at PC13, GPIO at PA2/PA3) may still apply."
- "Instrument-side bench wiring from the repo does NOT apply — please provide your
  {user_instrument} connections."
- "Note: the repo test requires GPIO capture capability. Confirm whether your instrument
  supports this."

Do NOT say:

- "Wiring confirmed." (when only target-side LED/GPIO was agreed to)
- "Setup matches." (when instrument-side bench wiring is unknown)
- "Ready to run." (when capture path is unresolved)

## Preserve The Value Of Known Mature Paths

This policy is not a refusal. The system should still use known repo support as a
strong starting point.

Desired behavior:
- identify the known path and say so clearly
- label it as candidate/reference until real setup is confirmed
- be helpful by listing exactly what the user still needs to provide
- once confirmed, use the confirmed real setup to prepare a runnable path

Avoid overcorrecting into excessive hedging or unhelpful defensiveness.
The goal is accurate confidence, not low confidence.

## Example: Good Behavior For A Known-Board Request

User says: "Please create a project for an STM32F411 board."

Good response structure:

```
A. Known from repo:
   - Candidate path: stm32f411ceu6 (WeAct Black Pill V2.0)
   - Candidate instrument: esp32jtag @ 192.168.2.103 (from repo config)
   - Candidate test plan: stm32f411_gpio_signature (PA2/PA3 toggle, PC13 LED)
   - Candidate wiring: PA2→P0.0, PA3→P0.1, SWD→P3, GND→probe GND

B. Assumed but not confirmed:
   - Whether your board is the same WeAct Black Pill V2.0 variant
   - Whether you have or plan to use esp32jtag as your instrument
   - Whether your wiring matches the repo bench_setup
   - What your intended first experiment is

C. Still needed from you:
   - Which exact STM32F411 board variant do you have?
   - What debug/flash instrument are you using?
   - Are you connected per the repo wiring, or different?
   - What should the first test demonstrate? (GPIO toggle, LED blink, UART, etc.)

D. Next step:
   - Confirm or correct the above — then I can prepare a runnable path
     that matches your real setup instead of only the repo reference.
```

Not acceptable:

```
Your STM32F411 project is ready. Using esp32jtag @ 192.168.2.103.
Wiring: PA2→P0.0, PA3→P0.1. Ready to flash.
```
(This treats unconfirmed repo facts as if they are the user's confirmed real setup.)

## Relationship To Adjacent Policies

- `ael_domain_response_contract_v0_1.md`: **outer container for this policy.**
  The domain response contract defines the four-section response structure
  (System Domain / User Project Domain / Branch Capability / Cross-Domain Link).
  This clarify-first policy applies *within* the User Project Domain section —
  at the point where the system identifies a candidate repo path and must
  solicit user confirmation before treating it as the user's real setup.
- `confirm_before_generation_policy_v0_1.md`: sequential companion.
  Clarify-first governs the *identification* stage (is this the right path?).
  Confirm-before-generation governs the *action* stage (are we ready to generate?).
  Both must be satisfied before any generation or execution proceeds.
- `user_project_creation_skill.md`: this policy adds the clarify-first rule to
  the known-board case within the project creation workflow. Also defines the
  Option B (external bench) response contract.
- `external_bench_execution_boundary_v0_1.md`: defines what AEL can and cannot
  do when the user's instrument is not reachable from the current machine.
  When instrument mismatch is confirmed here, execution defaults to Mode B there.
- `plan_stage_readiness_summary_skill.md`: that skill applies post-plan. This
  policy applies earlier — at the project creation or candidate path identification
  stage — before any plan is even run.
- `example_runtime_readiness_classification_v0_1.md`: the readiness states defined
  here align with that classification. A `candidate_path_identified` state
  corresponds to at most `blocked_missing_bench_setup` in that model.
- Unknown-board policy: this policy is strictly for known boards. Unknown or
  unsupported boards follow a separate workflow.
