# docs/night_tasks_agent_v0_8.md
# AEL Agent v0.8 — Review Pack + Execution Transparency + Nightly Merge Readiness

## Goal

Upgrade the autonomous workflow so that every AI-generated branch is:

1. Easy for humans to review
2. Transparent about what actually executed
3. Clearly marked as merge-ready or not

v0.8 focuses on **reviewability and trust**, not new automation power.

---

# Core Improvements

## 1. Automatic Review Pack (PR-style summary)

For every agent branch created during `ael nightly`, generate a review document:

Path:

    reports/pr_<branch>.md

Contents must include:

### Header

- Branch name
- Task title
- Task ID
- Execution timestamp
- Execution mode (codex/offline/noop)

Example:

    Branch: agent/20260304/gpio-test
    Task: develop gpio golden test
    Task ID: 20260304_123456
    Execution Mode: codex

### Summary

Short description of what the agent attempted.

### Files Changed

Output of:

    git diff --name-status main...HEAD

### Diff Summary

Output of:

    git diff --stat main...HEAD

### Evidence

Artifacts produced by the task:

- plan.json
- result.json
- run logs
- test results

### Reproduction Instructions

Example command to reproduce locally:

    python3 -m ael submit "<original prompt>"

### Merge Recommendation

Field generated automatically:

    merge_ready: yes | no

---

## 2. Execution Transparency

Currently some tasks may finish instantly when Codex is disabled.

Add explicit execution metadata everywhere.

Update task result schema:

    execution_mode: codex | offline | noop

Add field:

    downgrade_reason

Examples:

    downgrade_reason: codex_disabled
    downgrade_reason: planner_fallback

Ensure these fields appear in:

- result.json
- plan report
- nightly report

---

## 3. Nightly Merge Readiness Scoring

Enhance nightly report:

Path:

    reports/nightly_<YYYY-MM-DD>.md

Add table:

| Branch | Task | Status | Execution Mode | Tests | Merge Ready |
|------|------|------|------|------|------|
| agent/... | gpio test | OK | codex | PASS | YES |

Rules for `merge_ready`:

YES only if:

- plan completed successfully
- no downgrade to noop
- all smoke gates passed
- branch contains code changes

Otherwise:

    merge_ready: NO

---

# Implementation Tasks

## Task 1 — Review Pack Generator

Create module:

    ael/review_pack.py

Functions:

    generate_review_pack(branch, task, artifacts)

Output markdown report.

---

## Task 2 — Execution Metadata

Update:

    ael/agent.py
    ael/planner.py
    ael/bridge_task.py

Ensure result schema always includes:

    execution_mode
    downgrade_reason

---

## Task 3 — Nightly Report Upgrade

Update:

    ael/nightly_report.py

Add merge readiness logic.

---

## Task 4 — Smoke Test

Create:

    tools/review_pack_smoke.py

Test:

1. Create dummy branch
2. Simulate task artifacts
3. Generate review pack
4. Verify report fields exist

Expected output:

    [REVIEW_PACK_SMOKE] OK

---

# Validation Gates

After each commit run:

    python3 -m py_compile ael/*.py tools/*.py

    python3 tools/ael_guard.py --fast

    python3 tools/agent_smoke.py

    python3 tools/bridge_smoke.py

    python3 tools/plan_smoke.py

    python3 tools/nightly_smoke.py

    python3 tools/review_pack_smoke.py

---

# Commit Strategy

Commit 1

    feat(review): add review pack generator

Commit 2

    feat(agent): add execution metadata

Commit 3

    feat(report): nightly merge readiness scoring

Commit 4

    test(review): add review_pack_smoke gate

---

# Acceptance Criteria

The following workflow must work:

Run nightly:

    python3 -m ael nightly

Outputs:

- agent branches
- nightly report
- review pack for each branch

Files expected:

    reports/nightly_<date>.md
    reports/pr_<branch>.md

Reports must include:

- execution mode
- downgrade reason
- merge_ready decision
