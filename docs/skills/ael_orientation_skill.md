# AEL Orientation Skill

## Purpose

`ael_orientation` handles conversational entry-point questions — greetings,
"what does this system do?", "how can you help me?", "where do I start?" — and
routes the user to the right next step based on their context.

It is the first skill that should activate when the user has no specific
technical question yet. Its job is to establish context, set accurate
expectations, and identify the right entry path.

Supporting docs:

- `docs/what_is_ael.md` — authoritative short answer on what AEL is
- `docs/skills/ael_repo_answering_skill.md` — for follow-up system questions
- `docs/skills/user_project_answering_skill.md` — for follow-up project questions

---

## Trigger / When To Use

Use this skill when the user says something like:

- "Hello" / "Hi" / "哈喽" / any greeting
- "What is this system?" / "What does AEL do?"
- "How can you help me?" / "What can you do?"
- "I'm new here, where do I start?"
- "I have a board, what should I do?"
- Any general opener with no specific technical target yet

Do NOT use this skill when:

- The user has already named a specific board, test, or project
  (use `ael_repo_answering_skill` or `user_project_answering_skill` instead)
- The user is asking a specific technical question with enough context
  (answer directly from the appropriate authority source)

---

## User Context Detection

Before answering, determine which context the user is in by running:

```
python3 -m ael project list
python3 -m ael inventory list --format text
```

Then classify into one of four contexts:

### Context A — New user, no board named yet

Signals:
- `project list` returns `project_count: 0`
- user has not mentioned a specific MCU or board name

Response path: Brief AEL intro → ask "what board do you have?"

### Context B — New user, specific board already mentioned

Signals:
- user has named a board in their message ("I have a Blue Pill", "STM32F411", "Pico")
- no projects yet

Response path: Run alias lookup (configs/known_boards.yaml) → if known, clarify-first
A/B/C/D output (see known_board_clarify_first_policy_v0_1.md) → if unknown, bootstrap path.

### Context C — Returning user with existing projects

Signals:
- `project list` returns one or more projects

Response path: Summarize active project status → point to current blocker or next action.
Do not re-explain AEL basics unless asked.

### Context D — Meta capability question ("what can AEL do?")

Signals:
- user is asking about AEL's capabilities in general, not about a specific board
- "what boards are supported?", "what tests exist?", "what can you validate?"

Response path: Read from `ael inventory list` for current truth → summarize supported
boards, test types, and lifecycle stages.

---

## Procedure

1. Run `python3 -m ael project list` to detect user context.
2. Classify into Context A / B / C / D.
3. Apply the matching response template below.
4. State the source of any information given (CLI output, inventory, known_boards.yaml).
5. End with one concrete, actionable next question or command.

---

## Response Templates

### Context A — New user, no board named

```
AEL is a hardware validation system for embedded MCU boards.
It helps you build, flash, and validate board behavior using structured tests
and bench instruments — and records evidence of what passed.

Currently supported: [N] boards with tests.
Source: python3 -m ael inventory list

To get started, I need one thing from you:
  What board or MCU are you working with?

(Common examples: STM32F411 Black Pill, Blue Pill, Raspberry Pi Pico, ESP32-C6)
```

### Context B — Specific board mentioned

Run: `python3 -m ael project create --target-mcu "<board_name>"`

The alias resolver and bootstrap will handle the rest.
Then apply the known-board clarify-first A/B/C/D output from the create command.
Do not add paraphrasing on top of it.

### Context C — Returning user with project(s)

```
Welcome back. Here is where your project(s) stand:

[output of python3 -m ael project list]

To continue from where you left off:
  python3 -m ael project answering-context <project_id>

Your most recent action and next recommended step are shown there.
```

If there is exactly one project with `current_blocker` set:

```
Active blocker: <blocker>
Suggested next: <next_recommended_action>
```

### Context D — Meta capability question

```
What AEL currently supports:
  [output of python3 -m ael inventory list --format text — board list and test names]

AEL can help you:
  - run structured validation tests on a supported board
  - create a project for a new or unknown board (bootstrap workflow)
  - track what is confirmed vs assumed about your real setup
  - record test evidence and lifecycle state

AEL cannot:
  - detect or connect to your hardware remotely
  - confirm your wiring is correct without you telling it
  - substitute for real bench measurement
  - validate a board that has not been physically set up and connected
```

---

## What AEL Cannot Do — Required In All Orientation Responses

Every orientation response must include or be ready to state:

- AEL does not know whether your hardware is physically connected
- AEL does not know whether your wiring matches the repo reference
- AEL cannot run a test on a board that has not been confirmed as ready
- "Supported" means there is a validated repo path — not that your board is ready to run

This boundary must not be softened. It is a safety property of the system,
not a limitation to apologize for.

---

## Domain Separation Rule

Orientation responses must keep the following distinct:

| What | Where it comes from |
|---|---|
| What AEL supports in general | `ael inventory list` (system domain) |
| What your specific project has done | `ael project list / status / answering-context` (user project domain) |
| What your board's real setup is | Only from your own confirmations — never inferred from repo |

Do not mix system-domain facts ("stm32f411ceu6 is supported") with user-domain
facts ("your board is ready to run") unless the user has explicitly confirmed
the connection.

---

## Compact One-Line AEL Description

Use this when the user needs a very short answer:

> AEL is a structured hardware validation system: you give it a board and an
> instrument, it builds, flashes, and verifies — and records what passed.

---

## Fallback

If context cannot be determined (project list fails, inventory unavailable):

- Give the one-line description
- Ask what board the user is working with
- Do not guess current state

---

## Summary

`ael_orientation` routes general questions to the right entry path without
over-explaining. It detects whether the user is new or returning, named a
board or not, and asking about capabilities or their own project. It always
ends with one concrete next step — and always clearly separates what AEL
knows from the repo from what the user must confirm from their real setup.
