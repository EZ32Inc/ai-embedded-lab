# AEL Skills and Workflow Notes

## Purpose

This directory stores reusable engineering knowledge extracted from real AEL development and bench work.

These documents are intended to capture:
- troubleshooting workflows
- recurring diagnostic patterns
- design and policy clarifications
- operational guidance that should be reused in future work

The goal is to make important experience explicit, reusable, and easier for future AI/Codex/humans to apply.

## Why We Are Doing This

AEL development is now producing a growing amount of valuable practical knowledge:
- how to diagnose intermittent bench failures
- how to interpret verification behavior
- how to reason about resource locking and concurrency
- how to distinguish architecture issues from bench-side issues
- how to apply repeatable engineering workflows to real hardware problems

If this knowledge is not written down, it will be repeatedly rediscovered.
Writing it down now is the fastest and lightest way to preserve and reuse it.

## Current Approach

For now, AEL skills are stored as simple Markdown documents under `docs/skills/`.

This is intentionally lightweight.

At this stage, the priority is:
1. capture useful knowledge quickly
2. make it reusable
3. keep development moving

We are not yet building a formal skills engine or workflow execution system.
These Markdown files are the first practical step.

## What These Documents Are

A skill document should be a reusable engineering note, workflow, or troubleshooting guide.

It should help answer questions like:
- if this kind of problem happens again, what should we check?
- what evidence should we collect?
- how should we classify the problem?
- what conclusions are already known?
- what remains unresolved?

## What These Documents Are Not

These documents are not:
- raw session logs
- timeline-style summaries
- casual notes
- general brainstorming text

A session summary records what happened.
A skill document captures what should be reused next time.

## Writing Guidelines

Each skill document should be:
- practical
- concise
- structured
- reusable
- grounded in real AEL work

Prefer documenting:
- real problems already encountered
- workflows already used or clearly needed
- policy decisions that affect future work
- engineering patterns likely to recur

Do not present unverified hypotheses as established facts.
Separate:
- confirmed observations
- current working assumptions
- unresolved questions

## Suggested Structure

A skill document should usually include:

- Purpose
- Scope
- Background
- Failure / Issue Classes
- Required Observations
- Diagnosis Workflow
- Interpretation Guide
- Recommended Output Format
- Current Known Conclusions
- Unresolved Questions
- Related Files
- Notes

Not every document must be identical, but this structure should be the default.

## Naming Convention

Use clear, topic-focused filenames in lowercase with underscores.

Examples:
- `esp32c6_intermittent_bench_failure.md`
- `default_verification_repeat_mode.md`
- `probe_fallback_policy.md`
- `worker_resource_locking.md`

Avoid vague names such as:
- `notes_1.md`
- `new_workflow.md`
- `thoughts.md`

## Evolution Plan

These Markdown skill documents are the starting point.

Later, some or all of this knowledge may be turned into:
- more formal workflow documents
- structured metadata
- machine-readable skill formats
- agent-usable diagnostic or execution guidance

For now, the rule is simple:
capture the knowledge first, formalize it later.

## Immediate Use

The first intended use is to create concrete reusable skill documents from current AEL work, such as:
- ESP32-C6 intermittent bench failure investigation
- default verification repeat mode guidance
- probe fallback policy
- worker resource locking

These will serve both as practical references and as examples for future skill documents.
