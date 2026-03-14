# User Project Cross-Domain Link Convention v0.1

## Purpose

This note defines the lightest v0.1 convention for representing links between:

- system domain
- user project domain

without introducing a heavy project-management subsystem.

## Core Rule

User-project objects should remain distinct from system-domain objects.

When a project depends on, reuses, or is motivated by system-domain work, that
relationship should be recorded as lightweight metadata, not as a new graph or
database.

## Minimal Metadata Convention

Recommended project-local fields:

- `domain`
- `project_user`
- `system_refs`
- `cross_domain_links`

Optional fields:

- `tool_branch`
- `system_change_status`
- `motivated_by_user_goal`

## Field Meaning

### `domain`

Use:

- `user_project_domain`

This makes the project-local domain explicit and keeps it distinct from system
artifacts.

### `system_refs`

List the canonical system-domain docs or assets that are most relevant to the
project.

Example:

- capability anchor status note
- setup/connection contract
- bring-up preparation note

### `project_user`

Use:

- `project_user`

This is the preferred lightweight user field for v0.1.

It identifies the user context associated with the project without implying a
full ownership or permission model.

### `cross_domain_links`

Record the specific reason the project is linked to system-domain work.

Example shape:

```yaml
cross_domain_links:
  - type: mature_capability_anchor
    target: stm32f411ceu6
    reason: project is anchored to the current mature F411 capability path
```

This keeps the link explainable without creating a heavier data model.

Relevant system-domain or cross-domain notes may also use:

- `for_project_user`
- `motivated_by_user_goal`

when they need to explain why a system change exists.

### `tool_branch`

Optional field for a branch-specific tool variant that matters to the project.

This is useful when the project currently depends on a non-canonical system
branch.

### `system_change_status`

Optional field describing how a related system change should be interpreted:

- `local_variant`
- `candidate_for_integration`
- `integrated`

Use this only when it adds real clarity.

### `motivated_by_user_goal`

Optional project-local or note-level field describing the concrete user goal
that motivated a related system change or linkage.

This helps keep user-project intent and system evolution connected without a
larger project-management model.

## Canonical vs Branch-Specific Guidance

### Keep branch-local when:

- the tool change helps only this project
- it is still experimental
- it is not yet stable enough for canonical AEL

### Consider canonical integration when:

- the system improvement is reusable
- it helps more than one board or project
- it is validated enough to justify broader adoption

## Summary

For v0.1, cross-domain links should be represented as:

- a few small metadata fields
- project-local notes
- references to existing system-domain authorities

This is enough to keep the distinction explicit without building a new
management system.

The user concept should remain lightweight:

- use `project_user`
- optionally use `for_project_user`
- optionally use `motivated_by_user_goal`
- do not introduce an account or permission system here
