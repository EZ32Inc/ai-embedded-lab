# User Concept in AEL v0.1

> Status: **implemented** — `project_user`, `for_project_user`, and `motivated_by_user_goal`
> are active in `projects/<id>/project.yaml` and the `project` CLI commands.
> This doc records the design rationale.

## Purpose

This note defines the user concept for AEL v0.1.

The goal is to keep the system lightweight while leaving a clean path for future extension.

AEL v0.1 should be user-aware, but not a full multi-user platform.

1. Core decision

AEL v0.1 should assume a single-user primary usage model.

At the same time, AEL should still include a lightweight user concept as a semantic hook for:

associating user projects with a user,

associating system-domain changes with the user goal or project that motivated them,

enabling future growth toward multi-user support without redesigning the model later.

This means:

support user,

but do not build a full user/account/permission system yet.

2. Why project_user instead of project_owner

For v0.1, project_user is preferred over project_owner.

Reason:

owner implies stronger authority, access control, and permission semantics,

user is lighter and better matches the current stage,

the immediate need is to express “which user context this project belongs to,” not to implement full ownership policy.

Therefore, v0.1 should use lightweight fields such as:

project_user

for_project_user

motivated_by_user_goal

rather than a strong ownership model.

3. What AEL should support now

AEL v0.1 should support a lightweight semantic user concept in the following places:

In user project metadata

For example:

project_user

In system-domain notes when relevant

For example:

for_project_user

for_project

motivated_by_user_goal

In cross-domain links

A system-domain change may explicitly record which project/user context motivated it.

This is enough for v0.1.

4. What AEL should NOT do yet

AEL v0.1 should not attempt to implement:

user accounts

authentication

authorization

fine-grained permissions

private vs shared project visibility rules

full collaboration logic

user-isolated workspaces as a system feature

These may become relevant later, but they would make v0.1 too heavy.

5. Collaboration model in v0.1

If multiple trusted users collaborate, the primary collaboration mechanism should remain Git.

In practice:

if a user can check out a project or branch,

that user can work on it,

commit changes,

and continue development using normal Git workflows.

AEL does not need to duplicate this with a separate collaboration system in v0.1.

This means the practical v0.1 assumption is:

project access and collaboration are handled primarily by Git/repository workflows, while AEL handles project/system semantics.

6. Trust model for v0.1

AEL v0.1 may assume a trusted shared environment.

That means:

users who can access the repo can see shared work,

AEL does not need to enforce internal visibility boundaries,

the user concept is semantic and organizational, not security-enforcing.

This keeps the model simple.

7. Why the user concept still matters in a single-user-primary model

Even in single-user-primary usage, the user concept is still useful because it lets AEL answer questions like:

What are my current projects?

What system-domain changes were made for my project?

Which user project motivated this tool change?

What work belongs to my current user context?

So even before full multi-user support, user is already valuable as a question/answer organizing concept.

8. Recommended v0.1 principle

AEL v0.1 is single-user primary, but user-aware.
The user concept exists as a lightweight semantic hook for project association and future extension, not as a full collaboration or permission system.
Multi-user collaboration should rely primarily on Git workflows at this stage.

9. Practical implication

For v0.1, the recommended approach is:

add project_user to user-project metadata,

optionally add for_project_user / motivated_by_user_goal to relevant system-domain or cross-domain notes,

avoid building account/permission infrastructure,

keep Git as the main collaboration mechanism,

leave the model open for future multi-user expansion.

