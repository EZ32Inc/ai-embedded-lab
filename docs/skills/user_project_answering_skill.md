# User Project Answering Skill

## Purpose

`user_project_answering` is a lightweight skill for answering user questions
about their own projects in AEL.

It is a companion to `ael_repo_answering_skill.md`, which covers system-domain
questions. This skill covers user-project-domain questions.

Supporting specs:

- `docs/specs/ael_user_question_layer_draft_v_0_1.md`
- `docs/specs/ael_system_domain_and_user_project_domain_memo_v_0_1.md`

## Trigger / When To Use

Use this skill when the user asks:

- What projects do I currently have?
- What is the current status of this project?
- What is the current blocker?
- What is the best next step?
- What is assumed versus confirmed?
- What did we learn last time before stopping?
- What should I clarify before continuing?
- Which project motivated this system change?

Do not use this skill for system-domain questions such as:
- What is included in default verification?
- Is board X part of the AEL baseline?

For those, use `ael_repo_answering_skill.md`.

## Domain Separation Rule

> User-project history and system-baseline history must remain distinct,
> even when both are modified by the same user.

- a question about a user's project → answer from `projects/<id>/`
- a question about AEL system state → answer from system-domain sources
- a cross-domain question (why was this system change made?) → answer
  from `for_project` / `motivated_by_user_goal` fields on the relevant
  system-domain note

## Authority Source Map

| Question | Primary authority | Secondary authority |
|---|---|---|
| What projects do I have? | `python3 -m ael project list` | `projects/*/project.yaml` |
| What is the status of project X? | `python3 -m ael project status <id>` | `projects/<id>/project.yaml` |
| What is the current blocker? | `current_blocker` field in `project.yaml` | `projects/<id>/session_notes.md` |
| What is the next recommended action? | `next_recommended_action` field in `project.yaml` | `session_notes.md` |
| What is assumed vs confirmed? | `confirmed_facts` / `assumptions` / `unresolved_items` in `project.yaml` | `session_notes.md` |
| What did we learn before stopping? | `projects/<id>/session_notes.md` | `project.yaml` last_action |
| What mature AEL path is this based on? | `closest_mature_ael_path` in `project.yaml` | system capability anchor note |
| Which project motivated system change X? | `for_project` / `motivated_by_user_goal` on system-domain note | `cross_domain_links` in `project.yaml` |

## Procedure

1. Identify the question class (project state / blocker / next step / history / cross-domain).
2. Run `python3 -m ael project list` or `python3 -m ael project status <id>` first when the answer lives there.
3. Fall back to reading `projects/<id>/project.yaml` directly if the CLI is unavailable.
4. Use `session_notes.md` for richer narrative context (stopping summaries, lessons learned).
5. Answer directly.
6. State the source.
7. Explicitly separate confirmed facts from assumptions when relevant.

## Compact Answer Templates

### What projects do I have?

- `project_count: N`
- For each: `project_id`, `status`, `target_mcu`, `next_recommended_action`
- Source: `python3 -m ael project list`

### What is the current status of project X?

- project name, status, target_mcu, closest_mature_ael_path
- current_blocker (or "none")
- next_recommended_action
- confirmed_facts vs assumptions vs unresolved_items
- Source: `python3 -m ael project status <id>`

### What is the current blocker?

- blocker summary (or "none known")
- why that is the blocker (from session_notes if richer context needed)
- best next step
- Source: `current_blocker` field, then `session_notes.md`

### What did we learn last time before stopping?

- concise stopping summary from `session_notes.md`
- what was proven
- what remains unresolved
- recommended restart point
- Source: `projects/<id>/session_notes.md`

### What is assumed vs confirmed?

- confirmed_facts: ...
- assumptions: ...
- unresolved_items: ...
- Source: `project.yaml`

## Write-Back Rules

AI may update these fields in `project.yaml` when there is new information:

- `status`
- `current_blocker`
- `last_action`
- `next_recommended_action`
- `confirmed_facts` (append, do not remove without cause)
- `assumptions` (update when resolved or changed)
- `unresolved_items` (update when resolved)

AI may append to `session_notes.md` when a session produces new learnings,
blockers, or stopping summaries.

AI should **not** freely mutate `project_user`, `cross_domain_links`,
`closest_mature_ael_path`, or `system_refs` without clear reason.

## Fallback

If no `project.yaml` exists for the referenced project:

- say the project is not yet created
- suggest: `python3 tools/create_user_project_shell.py --help`

If `project.yaml` exists but is incomplete:

- answer from what is available
- explicitly note which fields are missing

## Summary

`user_project_answering` ensures AI answers user-project questions from
`project.yaml` and `session_notes.md` first, keeps user-project answers
distinct from system-domain answers, and can explain where each answer
came from.
