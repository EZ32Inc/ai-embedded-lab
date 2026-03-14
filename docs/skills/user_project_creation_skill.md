# User Project Creation Skill

## Purpose

This skill defines the lightweight v0.1 behavior for creating a user project in
AEL when the target board is already supported, or is highly similar to an
existing mature path.

Its first concrete worked example is:

- `stm32f411ceu6`

## Core Rule

Do not jump straight into code generation when the user says:

> "Please create a first example project for me."

For v0.1, do this instead:

1. create a lightweight empty-shell project
2. record the user goal
3. resolve the closest mature AEL board/capability path
4. record confirmed facts, assumptions, and unresolved items
5. present the best next setup/validation questions
6. only after that discuss generation, build, flash, and verify

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
- confirmed facts
- assumptions
- unresolved items
- best next questions

## Current Worked Example

For:

> "I have a board using stm32f411ceu6. Please create a first example project for me."

The skill should:

- create a shell under `projects/`
- anchor to the mature `stm32f411ceu6` path
- point to current F411 setup/capability docs
- avoid generating code until setup and first-example intent are clarified

## Relationship To Existing AEL Objects

- `default verification` remains a system-owned baseline object
- board/capability notes remain the technical authority
- the user project is only a lightweight user-facing working context

## Summary

For v0.1, user-project creation should be:

- shell first
- setup discussion second
- generation third
