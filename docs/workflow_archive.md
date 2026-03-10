# Workflow Archive

## Purpose

This is the minimal archival foundation for AEL workflow history.

It captures append-only workflow events now so retrieval, summaries, and broader workflow intelligence can be built later without changing the core run flow again.

Current scope is intentionally small:

- archive now
- analyze later

## Storage

Global append-only archive:

- `workflow_archive/events.jsonl`

Per-run append-only archive:

- `runs/<run_id>/workflow_events.jsonl`

The global archive is the simplest future ingestion point.
The per-run archive keeps each run self-contained and easy to inspect alongside `meta.json`, `result.json`, and `artifacts/run_plan.json`.

## Record Shape

Each line is one JSON object with schema:

- `schema`: current record schema id
- `timestamp`: ISO timestamp
- `category`: `workflow` or `runtime`
- `actor`: `user`, `assistant`, or `ael`
- `action`: interaction or runtime action such as `request`, `response`, `confirmation`, `correction`, `next_action`, `run_started`, `run_finished`
- `run_id`: AEL run id when available
- `session_id`: optional external session id
- `task_id`: optional external task id
- `board`: optional board metadata
- `test`: optional test metadata
- `probe`: optional probe metadata
- `instrument`: optional instrument metadata
- `stage`: current workflow stage or requested stage boundary
- `status`: event status
- `stage_execution`: executed/deferred stage summary when available
- `selected`: selected config file references when available
- `artifacts`: references to generated files when available
- `message`: optional interaction payload
- `result`: optional run result summary

Unknown fields are omitted or null instead of guessed.

Current probe/instrument metadata may include:

- resolved communication metadata
- capability-to-surface metadata

These are archived as run-context facts only. They are not yet interpreted as runtime routing policy by the archive layer.

## Current Capture Points

The run pipeline currently appends:

- runtime:
  - `run_started`
  - `run_finished`
- workflow interaction when provided by an outer wrapper:
  - user `request`
  - assistant `response`
  - user `confirmation`
  - user `correction`
  - assistant `next_action`

This keeps interaction history first-class while still preserving useful execution context.

## Optional Conversation Context

Conversation-relevant fields can be supplied by an external AI wrapper or orchestration layer through environment variables:

- `AEL_SESSION_ID`
- `AEL_TASK_ID`
- `AEL_USER_REQUEST`
- `AEL_AI_RESPONSE`
- `AEL_USER_CONFIRMATION`
- `AEL_USER_CORRECTION`
- `AEL_AI_NEXT_ACTION`

This is the current bridge for capturing user/AI interaction. It is intentionally simple and not presented as the final long-term integration interface.

If these are not present, the archive still records runtime workflow progress normally.

## Inspect Helper

A small CLI helper is available:

```bash
python3 -m ael workflow-archive show --limit 20
python3 -m ael workflow-archive show --run-id <run_id>
python3 -m ael workflow-archive show --source runs/<run_id>/workflow_events.jsonl
```

This only pretty-prints recent records. It does not add search, analytics, or summary logic.

## Why This Is Minimal

This is not a reporting or analytics subsystem.

It does not yet provide:

- search UI
- summaries
- correction mining
- friction analysis
- automatic recommendations

It only preserves structured workflow history so those features can be built later on top of real usage data.

## Likely Evolution Path

Later phases can build on the JSONL archive to add:

- session/task retrieval
- board/test history summaries
- stage transition summaries
- unresolved-item extraction
- repeated-friction analysis
- prompt/template refinement based on real workflow history
