# docs/night_tasks_agent_v0_3.md
# AEL Agent v0.3 — ChatGPT → Queue Interface

## Objective

Enable ChatGPT (or any external AI) to submit tasks into the AEL Agent queue automatically.

This creates the first **AI → AI development loop**:

ChatGPT → Task API → Queue → Agent → Codex → Repo → Report

This version focuses on **simple, stable functionality**.

---

# Phase 1 — Task API Server

Create a minimal HTTP server so external tools (ChatGPT, scripts, etc.) can submit tasks.

File:

ael/task_api.py

Responsibilities:

• Accept task submissions  
• Validate basic structure  
• Write task files into queue/inbox  
• Return task_id  

---

## Endpoint

### Health check

GET /health

Response:

```json
{
  "ok": true,
  "service": "ael-task-api",
  "version": "0.3"
}

Submit Task

POST /v1/tasks

Request:

{
  "task_id": "task_001",
  "description": "Implement GPIO golden test for STM32F103",
  "plan_file": "docs/night_tasks_gpio.md",
  "priority": "normal"
}

Behavior:

    Validate JSON

    Generate timestamp if missing

    Save to:

queue/inbox/task_001.json

Return:

{
  "accepted": true,
  "task_id": "task_001"
}

Phase 2 — Task File Format

Define simple queue task format.

Example:

queue/inbox/task_001.json

Content:

{
  "task_id": "task_001",
  "description": "Add STM32F103 GPIO golden test",
  "plan_file": "docs/night_tasks_gpio.md",
  "created_by": "chatgpt",
  "priority": "normal",
  "timestamp": "2026-03-04T22:30:00"
}

Agent will read this and run the associated plan.
Phase 3 — Agent Integration

Update agent runner.

File:

ael/agent.py

Add:

--api

mode.

Behavior:

ael agent --api

Starts the task API server.

Example:

python3 -m ael.task_api --port 8765

Phase 4 — Queue Ingestion

Agent must detect tasks submitted through API.

Existing queue directories:

queue/inbox
queue/running
queue/done
queue/failed

Workflow:

POST /v1/tasks
    ↓
queue/inbox/task_x.json
    ↓
agent runner picks it up
    ↓
moves to queue/running
    ↓
execute
    ↓
done / failed

Phase 5 — Task Execution

When agent picks a task:

    Read JSON

    Extract:

plan_file

    Execute existing runner logic:

run_plan(plan_file)

No new execution engine required.

Reuse:

Runner + AdapterRegistry

Phase 6 — CLI Tool (Optional but Recommended)

Create helper CLI:

ael/cli.py

Command:

ael submit docs/night_tasks_gpio.md

Behavior:

    Generate task_id

    Create task JSON

    POST to local API

Example usage:

ael submit docs/night_tasks_agent_v0_3.md

Phase 7 — Logging

When task is submitted:

Append entry to:

reports/task_log.md

Example:

[2026-03-04 22:30]

TASK ACCEPTED
task_id: task_001
plan: docs/night_tasks_gpio.md
source: task_api

Phase 8 — Validation

After implementing each step run:

Compile check:

python3 -m py_compile ael/*.py tools/*.py

Agent smoke test:

python3 tools/agent_smoke.py

Guard:

python3 tools/ael_guard.py --fast

Manual API test:

curl http://localhost:8765/health

Submit task:

curl -X POST http://localhost:8765/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_id":"test_1","plan_file":"docs/night_tasks.md"}'

Confirm file created:

queue/inbox/test_1.json

Phase 9 — Commit Strategy

Use incremental commits.

Commit 1

feat(api): add task_api server

Commit 2

feat(queue): support task JSON ingestion

Commit 3

feat(cli): add ael submit command

Commit 4

test(agent): add API smoke tests

Phase 10 — Expected Result

After completion:

You can submit tasks like this:

ChatGPT
    ↓
POST /v1/tasks
    ↓
AEL Queue
    ↓
Agent Runner
    ↓
Codex executes plan
    ↓
Report generated

This establishes the first AI-controlled development pipeline.
Phase 11 — Out of Scope

Not included in v0.3:

• multi-agent scheduling
• distributed runners
• web UI
• authentication

These belong to future versions.
