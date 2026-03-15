# AEL Agent Answering Guide

## Purpose

This guide defines how an AI agent should answer factual questions about AEL formally and consistently.

It is intended for:

- Codex
- Gemini CLI
- other AI agents working in or around this repo

It is not an architecture spec or a runtime feature. It is an answering discipline.

## Core Rule

When answering factual AEL questions, use the strongest current source available, not the most convenient source.

Preferred order:

1. resolved CLI output
2. current configs, manifests, and specs
3. implementation code
4. older narrative docs only as supporting context

## Truth Layers

Use these terms explicitly when needed.

### Architecture truth

What AEL says it is at the conceptual level.

Examples:

- top-level architecture
- meaning of Instrument, Connection, Workflow Memory, Skills
- intended system boundaries

Primary sources:

- `docs/specs/ael_architecture_v0_2.md`
- related current spec docs

### Config truth

What the current repo declares should be true.

Examples:

- board wiring assumptions
- instrument communication metadata
- plan definitions
- capability-surface declarations

Primary sources:

- `configs/boards/*.yaml`
- `configs/instrument_types/*.yaml`
- `configs/instrument_instances/*.yaml`
- `assets_golden/instruments/*/manifest.json`
- `tests/plans/*.json`

### Resolved truth

What AEL currently resolves after applying config selection, normalization, and planning logic.

Examples:

- resolved instrument surfaces
- resolved test connection setup
- resolved stage behavior summary

Primary sources:

- `python3 -m ael instruments describe --id <id>`
- `python3 -m ael inventory describe-test --board <board> --test <test>`
- `python3 -m ael inventory describe-connection --board <board> --test <test>`
- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`

### Runtime truth

What actually happened in an execution or health check.

Examples:

- default verification result
- doctor status
- actual preflight failure
- actual flash or verify result

Primary sources:

- `python3 -m ael instruments doctor --id <id>`
- `python3 -m ael connection doctor --board <board> --test <test>`
- `python3 -m ael verify-default run`
- `python3 -m ael verify-default state` — derived state object (health, blocker, validated tests)
- `python3 -m ael board state <board_id>` — per-board capability state
- run artifacts in `runs/`

### User project truth

What a user's own project currently declares about its status, goals, and blockers.

Examples:

- user project list and status
- current project blocker
- next recommended action for a project
- confirmed facts vs assumptions vs unresolved items
- session notes and stopping summaries

Primary sources:

- `python3 -m ael project list`
- `python3 -m ael project status <id>`
- `python3 -m ael project questions <id>`
- `projects/<id>/project.yaml`
- `projects/<id>/session_notes.md`

Write-back sources (AI may update these):

- `python3 -m ael project update <id> --set-blocker/--set-status/--set-next-action/...`
- `python3 -m ael project append-note <id> <text>`

Create:

- `python3 -m ael project create --target-mcu <mcu>`

Domain rule: user project answers must remain separate from system-domain answers.
See `docs/skills/user_project_answering_skill.md`.

### Known-board setup confirmation

When a user requests a project or experiment for a known board, repo facts
(board config, instrument profile, test plan, bench_setup) are reference
starting points only — they are NOT confirmed facts about the user's real setup.

The agent must:

- identify the candidate repo path and say so explicitly
- treat it as a reference/candidate until the user confirms their real setup
- output a structured section showing what is known, what is assumed, what is
  still needed, and what the next step is

The agent must NOT:

- state that the user's board is ready to run solely because a repo path exists
- inherit repo instrument/wiring as if they are definitely the user's real setup
- omit the missing-info output after identifying a candidate path

When the user's instrument is external / user-local (not reachable from the
current AEL machine), the agent must NOT attempt to run flash or debug tools
against it. The correct response stops at: build locally → report artifact →
provide user-side flash commands → provide verification instructions.

Policy and response structure:
`docs/specs/known_board_clarify_first_policy_v0_1.md`

Execution boundary for external-bench paths:
`docs/specs/external_bench_execution_boundary_v0_1.md`

## Source Priority

### 1. Resolved CLI Output

Use a resolved CLI command first whenever one exists for the question.

Examples:

- instrument identity and surfaces:
  - `python3 -m ael instruments describe --id <id>`
- instrument health:
  - `python3 -m ael instruments doctor --id <id>`
- test and bench setup:
  - `python3 -m ael inventory describe-test --board <board> --test <test>`
  - `python3 -m ael inventory describe-connection --board <board> --test <test>`
- stage meaning:
  - `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`
- connection consistency:
  - `python3 -m ael connection doctor --board <board> --test <test>`

Why:

- it is the best current formal view of resolved AEL state
- it reflects config merging and normalization
- it reduces stale or partial answers

### 2. Current Configs, Manifests, and Specs

Use these when the question is about declared structure, intended setup, or canonical metadata.

Examples:

- architecture:
  - `docs/specs/ael_architecture_v0_2.md`
- operator overview:
  - `docs/what_is_ael.md`
- instrument and connection specs:
  - `docs/specs/ael_instrument_spec_v0_22.md`
  - `docs/specs/ael_connection_spec_v0_1.md`
- board, instrument, and test declarations:
  - `configs/boards/*.yaml`
  - `configs/instrument_types/*.yaml`
  - `configs/instrument_instances/*.yaml`
  - `assets_golden/instruments/*/manifest.json`
  - `tests/plans/*.json`

### 3. Implementation Code

Use code:

- for behavior details
- when no better resolved CLI or config/spec source exists

Do not use code:

- as the first source for formal identity
- as a replacement for resolved CLI or current config/spec sources when those exist

Typical files:

- `ael/adapters/*`
- `ael/pipeline.py`
- `ael/strategy_resolver.py`
- `ael/connection_model.py`
- `ael/instrument_view.py`

### 4. Older Narrative Docs

Use older docs only as supporting context, not as the sole source of current truth.

If a narrative doc conflicts with current config or resolved CLI output, prefer the current config or CLI output.

## Current vs Historical Questions

Be explicit about whether the user is asking about the present or the past.

For current-state questions:

- prefer current resolved sources first
- then current config/spec sources

For historical questions:

- current config should not be used naively as the answer
- use change context such as:
  - git history
  - dated notes
  - prior docs
  - prior run artifacts

If the answer is historical, say so clearly.

## Required Discipline

Agents should:

- distinguish architecture truth, config truth, resolved truth, and runtime truth
- mark provisional assumptions explicitly
- prefer resolved views over raw manifest snippets when available
- avoid answering from memory when a formal local source exists

Agents should not:

- answer current-state questions from stale docs alone
- treat guessed bench assumptions as confirmed facts
- cite raw code first when a resolved CLI path already exists
- use current config as proof of historical state

## Minimal Expectation For Formality

An answer is formal enough when:

- it uses the correct truth layer
- it can point to a specific command or file
- it makes assumptions visible
- it separates current-state facts from historical context when needed

## Summary

The main answering rule is:

- use resolved CLI when available
- then use current config/spec sources
- then use code for behavior details
- use older docs only as support

That is the baseline for consistent AEL answers across agents.
