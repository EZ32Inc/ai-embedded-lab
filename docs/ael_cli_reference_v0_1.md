# AEL CLI Reference v0.1

This document lists all available `ael` commands, their purpose, typical usage,
and key output fields.

All commands run from the repo root: `python -m ael <command>` or `ael <command>`
(if installed).

---

## Overview Commands

### `ael status`

Unified system domain + user project domain overview. The primary entry point
for understanding the current state of everything.

```bash
ael status
ael status --projects-root projects --runs-root runs
```

**Output sections:**
- `=== System Domain ===` — lists system main DUTs (`assets_golden/`) with
  `verified` status, branch DUTs (`assets_branch/`) with `lifecycle_stage`,
  promote candidates, and default verification pass rate
- `=== User Project Domain ===` — lists all user projects with `status`,
  `capability_source` (main/branch), and branch `capability_ref`
- `=== Cross-Domain Links ===` — branch capabilities linked to user projects,
  current lifecycle stage, and promote path

---

### `ael board state <board_id>`

Capability state for a specific board: run history, health, source domain.

```bash
ael board state stm32f411ceu6 --format text
ael board state stm32h743_draft --format text
```

**Key output fields:**
- `source: golden | branch | user` — which namespace this DUT lives in
- `lifecycle_stage: merged_to_main | validated | runnable | draft`
- `health_status: pass | partial_pass | fail | unknown`
- `validated_tests` / `failing_tests`

**Default format:** JSON. Use `--format text` for human-readable output.

---

### `ael inventory list`

Full DUT and test inventory across all namespaces.

```bash
ael inventory list --format text
```

**Output:** Each DUT with `[branch]` or `[golden]` tag, `stage=<lifecycle>`,
and all associated tests.

---

### `ael doctor`

Check instrument connectivity and bench health.

```bash
ael doctor
ael doctor --instrument <ip:port>
```

---

## Project Commands

### `ael project create`

Create a new user project. Resolves the closest system capability (mature/inferred/unknown),
creates a draft capability in `assets_branch/` if needed, and outputs the domain assignment.

```bash
ael project create \
  --target-mcu stm32h743zit6 \
  --project-name "H743 full test" \
  --user-goal "test all peripherals" \
  --project-user alice
```

**Key output for mature path (copy hit):**
- A/B/C/D structured block: known repo facts / assumptions / still needed / next step
- `capability_source: main`

**Key output for inferred/unknown path (copy miss):**
- Bootstrap result: DUT id, manifest path, board config path, `lifecycle: draft`
- `capability_source: branch`, `capability_ref: <dut_id>`
- Lifecycle path: `draft → runnable → validated → merge_candidate → merged_to_main`

**Stored in `projects/<id>/project.yaml`:**
`domain`, `project_user`, `path_maturity`, `capability_source`, `capability_ref`,
`confirmed_facts`, `assumptions`, `unresolved_items`, `cross_domain_links`

---

### `ael project list`

List all user projects with domain and capability source.

```bash
ael project list
ael project list --projects-root projects
```

**Output per project:**
`domain`, `target_mcu`, `path_maturity`, `capability_source`,
`capability_ref` (if branch), `status`, `next_recommended_action`

---

### `ael project status <project_id>`

Detailed status for one project.

```bash
ael project status stm32h743_bringup
```

**Key output fields:**
`domain`, `path_maturity`, `capability_source`, `capability_ref [branch capability | system main]`,
`confirmed_facts`, `assumptions`, `unresolved_items`, `run_evidence`

---

### `ael project questions <project_id>`

Guided next questions for a project. Branches on `path_maturity`.

```bash
ael project questions stm32h743_bringup
```

For **mature** paths: confirmation checklist (board variant, instrument, wiring, test intent).
For **inferred/unknown** paths: open questions about MCU details, board, instrument.

---

### `ael project run-gate <project_id>`

Gate check before running. Must pass before `ael run` is used with a project flag.

```bash
ael project run-gate stm32h743_bringup
```

**Readiness states:**
- `confirmed_enough_to_prepare` — gate open
- `partially_confirmed` — gate open with warnings
- `candidate_path_identified` — gate blocked, need confirmations
- `branch_capability_runnable` — branch DUT at runnable stage, gate open
- `branch_capability_draft` — gate blocked, fill PLACEHOLDERs first
- `branch_capability_missing` — gate blocked, branch DUT not found

---

### `ael project update <project_id>`

Update project fields.

```bash
ael project update stm32h743_bringup --set-status runnable
ael project update stm32h743_bringup --append-confirmed-fact "Board confirmed: H743ZIT6"
ael project update stm32h743_bringup --set-blocker "instrument offline"
```

---

### `ael project link-run <project_id>`

Link a completed run result to a project and update run evidence.

```bash
ael project link-run stm32h743_bringup \
  --run-id 2026-03-17_10-30-00_stm32h743_gpio_loopback \
  --ok
```

---

### `ael project show-cross-domain-links <project_id>`

Show how this user project links to the system domain.

```bash
ael project show-cross-domain-links stm32h743_bringup
```

**Output:**
- `capability_source` and `capability_ref`
- Current `lifecycle_stage` of the branch DUT
- Full lifecycle path with current stage highlighted: `[draft] → runnable → ...`
- Next steps to advance lifecycle and promote
- Cross-domain impact: "when promoted, enters assets_golden/ as system main capability"

For **main** projects: `cross_domain_links: (none) — uses system main capability`

---

### `ael project append-note <project_id>`

Append a note to the project's session notes.

```bash
ael project append-note stm32h743_bringup --note "SWD confirmed working"
```

---

### `ael project intake <project_id>`

Interactive or non-interactive fact collection — write confirmed facts from a
structured checklist directly into project.yaml.

```bash
ael project intake stm32h743_bringup
ael project intake stm32h743_bringup --non-interactive
```

---

## DUT / Capability Commands

### `ael dut set-lifecycle`

Advance the `lifecycle_stage` of a branch or user DUT.

```bash
ael dut set-lifecycle --id stm32h743_draft --stage runnable
ael dut set-lifecycle --id stm32h743_draft --stage validated
ael dut set-lifecycle --id stm32h743_draft --stage merge_candidate
```

**Valid stages:** `draft → runnable → validated → merge_candidate → merged_to_main`

Stage must advance in order. `merged_to_main` is set automatically by `dut promote`.

---

### `ael dut promote`

Promote a branch capability to system main (`assets_golden/`).

```bash
ael dut promote --id stm32h743_draft
ael dut promote --id stm32h743_draft --as-id stm32h743zit6
```

**Gate 1:** `lifecycle_stage` must be `merge_candidate`.
**Gate 2:** `compile_validation` must be `passed`.
**Gate 3:** Required metadata fields must be present (id, mcu, family, build_type, flash_method).

On success: DUT moves to `assets_golden/duts/`, `lifecycle_stage` set to `merged_to_main`.

---

### `ael dut show-placeholders`

List unfilled PLACEHOLDER fields in a branch/user DUT before advancing lifecycle.

```bash
ael dut show-placeholders --id stm32h743_draft
ael dut show-placeholders --id stm32h743_draft --namespace branch
```

---

### `ael dut show-linked-projects`

Reverse lookup: which user projects reference this branch DUT?

```bash
ael dut show-linked-projects --id stm32h743_draft
```

**Output:** linked project list with status and user, plus promote path and cross-domain impact.

---

### `ael dut create`

Copy a DUT from `assets_golden/` to `assets_branch/` or `assets_user/`.

```bash
ael dut create stm32f411ceu6 stm32f411_variant --dest branch
```

Creates `assets_branch/duts/stm32f411_variant/` with `lifecycle_stage: draft`.

---

### `ael dut set-compile-validated`

Record compile validation result on a branch DUT (required for promote Gate 2).

```bash
ael dut set-compile-validated --id stm32h743_draft --result passed
ael dut set-compile-validated --id stm32h743_draft --result failed --note "linker error"
```

---

## Execution Commands

### `ael run`

Run a single test against a board.

```bash
ael run --board stm32f411ceu6 --test stm32f411_gpio_signature
ael run --project stm32h743_bringup --test stm32h743_gpio_loopback
```

When `--project` is given and the project has `capability_source: branch`,
the branch DUT is used automatically.

---

### `ael pack`

Run a test pack (multiple tests) against a board.

```bash
ael pack smoke_stm32f411 --board stm32f411ceu6
```

---

## Verification Commands

### `ael verify-default`

Manage and run the system-level default verification suite.

```bash
ael verify-default show                    # show current config
ael verify-default state --format text     # current pass/fail state
ael verify-default run                     # run all steps
ael verify-default repeat --limit 5        # repeat until failure, max 5 runs
```

Default verification is a **system domain** object — it tracks platform health
across all verified boards, not individual user project state.

---

## Lifecycle Summary

```
User project:    intake → plan → execute → review → closeout
                 (project.yaml: status field)

Branch DUT:      draft → runnable → validated → merge_candidate → merged_to_main
                 (manifest.yaml: lifecycle_stage field)
                 Promoted to system main via: ael dut promote

System main:     assets_golden/duts/<id>/manifest.yaml  lifecycle_stage: merged_to_main
Branch:          assets_branch/duts/<id>/manifest.yaml  lifecycle_stage: draft|runnable|...
```

---

*CLI Reference version: v0.1 — covers AEL as of 2026-03-17.*
