# AEL Agent Answering Guide

## Purpose

This guide defines how an AI agent should answer factual questions about AEL formally and consistently.

It is meant for:

- Codex
- Gemini CLI
- other AI agents working inside or alongside the AEL repo

It is not an architecture spec. It is an answering workflow.

## Core Rule

When answering factual AEL questions, use the most formal current source available, not the most convenient source.

Prefer:

1. resolved CLI output
2. active manifests, configs, and current specs
3. implementation code
4. older narrative docs only as supporting context

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

- this is the closest thing to the current formal runtime truth
- it already reflects config resolution and normalization
- it reduces the risk of answering from stale assumptions

### 2. Current Configs, Manifests, and Specs

Use these when the question is about structure, declared intent, or canonical metadata.

Examples:

- architecture and definitions:
  - `docs/specs/ael_architecture_v0_2.md`
  - `docs/specs/ael_instrument_spec_v0_22.md`
  - `docs/specs/ael_connection_spec_v0_1.md`
- instrument definitions:
  - `configs/instrument_types/*.yaml`
  - `configs/instrument_instances/*.yaml`
  - `assets_golden/instruments/*/manifest.json`
- board definitions:
  - `configs/boards/*.yaml`
- test intent:
  - `tests/plans/*.json`

### 3. Implementation Code

Use code when the question is about actual behavior and no better resolved CLI or spec source exists.

Examples:

- protocol/backend behavior
- exact command shape sent to hardware
- fallback logic
- error handling

Typical files:

- `ael/adapters/*`
- `ael/pipeline.py`
- `ael/strategy_resolver.py`
- `ael/connection_model.py`
- `ael/instrument_view.py`

### 4. Older Narrative Docs

Use older docs only as supporting context, not as the sole source of current truth.

If a narrative doc conflicts with current config or resolved CLI output, prefer the current config or CLI output.

## Standard Answer Pattern

For factual questions, prefer this structure:

1. direct answer
2. how it is known
3. formal source or command
4. caveat if any

Example:

- question:
  - `What is esp32jtag?`
- answer shape:
  - what it is
  - where its current formal definition comes from
  - which command shows the resolved view
  - any known provisional assumptions

## Common Question Classes

### "What is AEL?"

Primary sources:

- `docs/specs/ael_architecture_v0_2.md`
- relevant current CLI commands if the question is operational rather than architectural

### "What is instrument X?"

Primary sources:

- `python3 -m ael instruments describe --id <id>`
- instrument manifest or instance/type config
- backend code only if the user asks for protocol or implementation details

### "How do I use AEL?"

Primary sources:

- current CLI help
- workflow docs
- relevant spec or skill document

Do not answer this from architecture docs alone if the user is asking operationally.

### "What is the connection for board/test Y?"

Primary sources:

- `python3 -m ael inventory describe-connection --board <board> --test <test>`
- board config and test plan only as supporting evidence

### "How does stage X work?"

Primary sources:

- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`
- code if deeper behavior explanation is needed

## Required Discipline

Agents should:

- distinguish between declared config and confirmed runtime behavior
- mark provisional assumptions explicitly
- prefer resolved views over raw manifest snippets when available
- avoid answering from memory when a formal local source exists

Agents should not:

- answer current-state questions from stale docs alone
- treat guessed bench assumptions as confirmed facts
- cite raw code first when a resolved CLI path already exists

## Minimal Expectation For Formality

An answer is formal enough when:

- it uses the correct current source layer
- it can point to a specific file or command
- it makes assumptions visible
- it avoids mixing architecture truth, config truth, and runtime truth

## Summary

The main answering rule is simple:

- use resolved CLI when available
- then use current config/spec sources
- then use code
- use older docs only as support

This is the baseline for consistent AEL answers across agents.
