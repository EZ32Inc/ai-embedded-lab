# System Note Project Link Convention v0.1

## Purpose

This note defines the lightest v0.1 convention for system-domain notes that
need to explain why a system change exists in relation to a user project.

It is intentionally small.

## Use Only When Helpful

Do not add project/user linkage fields to every system note by default.

Use them only when a system-domain note would be clearer if it explicitly
records:

- which project motivated the system change
- which user context the project belongs to
- what user goal motivated the work

## Recommended Optional Fields

- `for_project`
- `for_project_user`
- `motivated_by_user_goal`

## Example

```yaml
for_project: stm32f411_first_example
for_project_user: local_user
motivated_by_user_goal: Create a first example project for a board using stm32f411ceu6
```

## Meaning

- `for_project`
  - the project-local context this system note is helping
- `for_project_user`
  - the lightweight user context associated with that project
- `motivated_by_user_goal`
  - the concrete user-facing goal that motivated the system-domain change

## Boundaries

These fields are:

- explanatory
- organizational
- cross-domain

They are not:

- a permission model
- an ownership system
- a collaboration subsystem

## Summary

For v0.1, if a system-domain note needs project linkage, use a few optional
fields and keep the rest of the system note canonical and system-focused.
