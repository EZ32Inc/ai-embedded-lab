# AEL Memo: System Domain and User Project Domain v0.1

## Purpose

This memo captures the current design conclusion for the next stage of AEL.

The goal is to clarify how AEL should distinguish:

- work that evolves the AEL system itself,
- work that belongs to a user’s own project,
- and the links between the two.

This distinction is important both for internal architecture and for user-facing question/answer behavior.

It also captures a core AEL insight:

> In the AI era, the tool itself is no longer a fixed external environment.
> It becomes an evolvable, versioned, validated part of the engineering workflow.

---

## 1. Why this distinction matters

In the traditional IDE/tool era, the tool and the user project were strongly separated.

- The tool was fixed.
- The user project was where change happened.
- Even with open-source tools, most users did not realistically modify the tool itself because the codebase was too large, too complex, too risky, and too expensive to validate.

This created a major limitation:

> Users could adapt their project to the tool, but they could not easily adapt the tool to the project.

AEL changes this.

Because AEL is AI-assisted, versioned with Git, and increasingly backed by validation flows, the tool itself can now be modified at much lower cost.

That means AEL must explicitly model two domains of work:

1. **system domain**
2. **user project domain**

---

## 2. System domain

The **system domain** contains work that evolves AEL/IEL itself.

Examples include:

- `default verification`
- baseline packs
- board support / capability integration
- inventory behavior
- workflow rules and skills
- docs/specs that define baseline system behavior
- validation rules for system-level capabilities
- branch-specific AEL tool variants

The purpose of system-domain work is to improve the platform itself.

System-domain changes may affect:

- baseline health
- future users
- board onboarding behavior
- default verification
- reusable engineering workflows
- system-owned documentation and skills

### Key property

`default verification` is always a **system-owned baseline object**, not a user project.

---

## 3. User project domain

The **user project domain** contains work that belongs to a user’s own goal.

Examples include:

- creating a first project for a board using `stm32f411ceu6`
- generating a LED blink example
- generating project-local implementation files
- project-specific validation work
- project-specific assumptions and setup discussion
- project-local notes, blockers, decisions, and next steps

The purpose of user-project work is to advance a specific user goal.

A user project may reuse:

- board capability knowledge
- validated patterns
- test plans
- workflow guidance
- baseline context

But it should not be confused with the system domain itself.

---

## 4. Cross-domain links

AEL must also explicitly recognize a third concept:

## Cross-domain links

A user project may expose a missing capability or a missing workflow in the system.
Then the system domain may change in order to support that project.
Then the user project continues using the improved system.

This is a normal and valuable AEL pattern.

Examples:

- a user project discovers a missing helper or validation path
- AEL gains a new skill or capability because of that need
- the project then resumes with the new system support

Therefore, AEL should not treat system changes and user-project changes as isolated worlds.
They are distinct, but linked.

---

## 5. The central rule

The key rule is:

> User-project history and system-baseline history must remain distinct, even when both are modified by the same user.

This means:

- the same user may work in both domains,
- the same conversation may touch both domains,
- but the resulting records, summaries, status answers, and closeout logic must not mix them together.

The distinction is based on **domain of work**, not on **identity of the user**.

---

## 6. AEL’s AI-era advantage

AEL’s advantage over traditional tool environments is not just that AI helps write project code.

AEL also enables users to participate in evolving the tool itself.

This is possible because AEL combines:

- AI-assisted modification,
- Git-based version history,
- repeatable validation,
- closeout and capability notes,
- baseline integration workflows.

As a result:

- system-domain changes are lower-cost,
- failures are recoverable,
- changes can be validated,
- useful improvements can become reusable system capabilities.

This is one of AEL’s most important differentiators.

---

## 7. Branches and project-specific tool variants

One especially important AI-era capability is this:

> The tool itself can have low-cost branch-specific variants.

In traditional tools, even if a tool was theoretically modifiable, it was rarely practical to create a project-specific tool variant.
The cost was too high.

In AEL, AI plus Git makes this realistic.

A user or developer can create a branch where the AEL tool itself has a special feature, helper, workflow, or diagnostic path that is useful only for:

- one board,
- one project,
- one environment,
- one special workflow.

That branch does not need to become the canonical system immediately.
It may remain a project-specific tool branch.

### This leads to an important distinction inside system domain:

#### Canonical system domain

- mainline AEL capabilities
- stable default verification
- baseline workflows
- reusable board/capability support

#### Branch-specific system variants

- experimental AEL tool changes
- project-specific system helpers
- board-specific temporary workflow extensions
- special diagnostics that are valuable only in one context

AEL should support both.

Not every useful system change must immediately enter the canonical baseline.

---

## 8. What should merge back, and what should not

AEL should distinguish between:

### Reusable system improvement

A change should be considered for mainline system integration when it:

- improves general capability,
- benefits multiple projects or boards,
- is stable enough to validate,
- does not create unnecessary fragility,
- fits baseline/default-verification semantics.

### Project-specific tool variant

A branch-specific system change may remain local when it:

- serves only one project,
- depends on one board/environment/workflow,
- is not yet mature enough for general baseline use,
- is useful but not generalizable.

This distinction should be natural, lightweight, and Git-friendly.

---

## 9. How this affects user-facing interaction

The distinction between domains is not only an internal implementation detail.
It should become part of the user-facing question layer.

When a user asks broad questions such as:

- What projects do I currently have?
- What changes have I made?
- What is happening in AEL right now?
- Why was this system change made?
- Which project motivated this tool change?

AEL should answer in a structured way using domain separation.

A natural top-level structure is:

### System domain

- current system work
- recent system changes
- baseline/default-verification status
- active or recent system blockers
- next recommended system-level action

### User project domain

- current user projects
- recent project changes
- project blockers
- project next steps

### Cross-domain links

- which user projects motivated which system changes
- which system improvements now support which projects
- why a particular system-domain change was introduced

This makes the system understandable without forcing the user to browse raw file trees.

---

## 10. Relationship to AI-first project management

AEL should not begin with a heavy project-management system.
It should remain lightweight.

The practical approach is:

- preserve files as the asset layer,
- preserve current system-owned baseline objects such as `default verification`,
- introduce lightweight user-project objects,
- use AI to retrieve, summarize, and answer questions,
- separate system-domain and user-project records,
- support cross-domain links where needed.

This means:

- the primary user interaction becomes question/answer,
- file trees become secondary,
- domain-aware summaries become the first organizing layer.

## 10.1 Lightweight user concept in v0.1

The user concept should remain lightweight in v0.1.

AEL should be:

- single-user primary
- user-aware

The `user` concept should exist mainly as a semantic hook for:

- associating a user project with a user context
- linking system-domain changes to the motivating project or user goal
- future extension toward multi-user support

It should not become:

- an account system
- an authentication system
- a permission model
- a collaboration platform

Preferred wording for v0.1:

- use `project_user`
- do not use `project_owner`

### Collaboration model

For v0.1, multi-user collaboration should remain primarily Git-based.

If multiple trusted users collaborate, normal Git branch/review workflows remain
the main collaboration mechanism.

AEL does not need to duplicate this with a separate collaboration system in
v0.1.

### Trust model

For v0.1, AEL may assume a trusted shared environment.

That means:

- users with repo access can see shared work
- AEL does not need to enforce visibility or access boundaries
- the user concept is organizational, not security-enforcing

---

## 11. Practical v0.1 implications

For v0.1, AEL should:

### Keep strong existing system objects

- `default verification`
- board/capability notes
- closeout notes
- repeat-validation notes
- inventory/runtime authorities

### Introduce lightweight user-project objects

For example:

- `projects/<project_id>/project.yaml`
- `projects/<project_id>/README.md`
- `projects/<project_id>/session_notes.md`

These may also include lightweight user-aware fields such as:

- `project_user`

### Keep the distinction explicit

When recording or summarizing work, AEL should know whether a change belongs to:

- `system_domain`
- `user_project_domain`
- `cross_domain_link`

When relevant, AEL should also support lightweight fields such as:

- `for_project_user`
- `motivated_by_user_goal`

This can begin as a lightweight convention rather than a heavy formal system.

### What to implement now

Implement now:

- lightweight `project_user` in project metadata
- optional `for_project_user` and `motivated_by_user_goal` in relevant
  system-domain or cross-domain notes when they add clarity
- user-aware question answering

### What to defer

Defer:

- accounts
- auth
- permissions
- broad collaboration logic
- user-isolated workspace mechanics
- private/shared visibility infrastructure

---

## 12. First concrete user-project scenario

The recommended first concrete v0.1 user-project scenario is:

> A user says: “I have a board using `stm32f411ceu6`. Please create a first example project for me.”

The first step should be:

- create a lightweight empty-shell user project,
- resolve the closest mature existing board/capability path,
- record assumptions vs confirmed facts,
- provide the best next questions,
- then continue with setup/wiring/validation discussion,
- then generate implementation and verification steps.

This is the natural place where user-project management begins to grow.

---

## 13. Final summary

AEL’s next-stage architecture should explicitly recognize that there are two major domains of work:

1. **system domain**
2. **user project domain**

These domains must remain distinct in history, status, validation, and closeout semantics.

At the same time, AEL must support cross-domain links, because user projects can and should drive useful evolution of the system itself.

This is one of AEL’s defining advantages in the AI era:

> the tool itself becomes an evolvable, branchable, validated part of the engineering workflow, not just a fixed external environment.

That should now be treated as a core AEL design principle.
