# AEL Core v0.1 Boundary Contract

## Purpose

This document defines the architectural boundaries of the **AEL Core**.

The goals are:

- keep AEL **board-agnostic**
- ensure **reproducible execution**
- prevent **core contamination**
- allow safe community contributions
- enforce a clear separation of responsibilities

AEL divides execution into well-defined pipeline stages.

---

# 1. AEL Execution Pipeline

The AEL execution model consists of six stages.

Plan → Preflight → Build → Run → Check → Report


### Stage overview

| Stage | Responsibility |
|------|---------------|
| Plan | Generate a deterministic RunPlan |
| Preflight | Validate environment readiness |
| Build | Produce execution artifacts |
| Run | Load/start the target system |
| Check | Validate system behavior |
| Report | Produce reproducible results |

Only **Build / Run / Check** interact with the DUT.

---

# 2. Plan Stage

## Purpose

Generate a deterministic **RunPlan**.

## Input

- board configuration
- probe configuration
- instrument configuration
- test definition
- optional pack configuration

## Output

RunPlan (pure data structure)

Example structure:

RunPlan
├─ build_step
├─ run_step
├─ check_steps[]
├─ merged_config
└─ recovery_policy


## Rules

Plan stage:

- MUST NOT access hardware
- MUST NOT open serial ports
- MUST NOT execute external commands
- MUST NOT probe device connectivity

Plan must be **side-effect free**.

---

# 3. Preflight Stage

## Purpose

Validate that the system environment is ready to execute the RunPlan.

## Input

RunPlan

## Output

PreflightReport

Example:

status: pass | warn | fail
findings:

    message
    guidance:

    suggested action


## Responsibilities

Preflight may verify:

- required tools exist
- required tool versions
- device node presence
- device permissions
- probe connectivity
- instrument connectivity
- measurement capability availability

## Failure Semantics

| Result | Behavior |
|------|---------|
| pass | execution continues |
| warn | execution continues with warning |
| fail | pipeline stops immediately |

Preflight failures **do not enter recovery loops**.

---

# 4. Execution Stages

The following stages perform DUT operations.

Build
Run
Check


## Build

Produces artifacts required for execution.

Examples:

- compile firmware
- build binaries
- package artifacts

---

## Run

Transitions the DUT into a state ready for verification.

Examples:

- flash firmware
- load RAM image
- reset target
- start program execution

---

## Check

Validates system behavior and collects evidence.

Examples:

- UART log observation
- GPIO signal verification
- voltage measurement
- protocol verification

Checks generate **evidence artifacts**.

---

# 5. Stage Result Contract

Each execution stage returns the following structure.

{
status: "success" | "fatal" | "recoverable",
reason: "machine_readable_code",
summary: "human_readable_message",
evidence: {...},
recovery: {
action: "...",
strategy: "...",
scope: "check | run | build | preflight | plan"
}
}


### Status semantics

| Status | Meaning |
|------|--------|
| success | stage completed |
| fatal | unrecoverable error |
| recoverable | failure may be auto-recovered |

Stages **must never implement retry loops internally**.

---

# 6. Recovery Model

Recovery is **not a pipeline stage**.

Recovery is controlled by the **Runner**.

Stages only report recoverable failures.

The Runner evaluates recovery policies and decides whether recovery should occur.

---

# 7. Recovery Rewind Anchors

The `scope` field determines where execution restarts.

| Scope | Restart Point |
|------|--------------|
| check | Check |
| run | Run → Check |
| build | Build → Run → Check |
| preflight | Preflight → Build → Run → Check |
| plan | Plan → Preflight → Build → Run → Check |

Default scope:

run


---

# 8. Recovery Policy

Recovery is governed by configuration.

Example:

recovery_policy:

retries:
check: 2
run: 2
build: 1
preflight: 0
plan: 0

allow:
- { action: reset, scope: run }
- { action: reconnect, scope: run }


If retry limits are exceeded, the pipeline stops and generates a report.

---

# 9. Report Stage

The Report stage records the entire run.

Typical artifacts include:

- RunPlan
- PreflightReport
- build logs
- run logs
- measurement data
- verification results
- final status

Reports ensure **full reproducibility**.

---

# 10. Core Boundary Rules

AEL Core must remain **generic**.

Core code must not contain:

- board names (esp32, stm32, rp2040, etc.)
- probe names
- toolchain specific assumptions
- board-specific logic
- tool-specific commands

Board and tool logic must exist only in:

configs/
adapters/
packs/


---

# 11. Design Principles

AEL follows these principles:

1. Plan defines the execution steps
2. Preflight validates readiness
3. Execution stages perform DUT actions
4. Runner controls recovery behavior
5. Policy defines recovery limits
6. Reports ensure reproducibility

Stages report facts.

Runner controls execution.

Configuration defines behavior.

---

# Summary

AEL Core v0.1 architecture:

Plan → Preflight → Build → Run → Check → Report


Recovery is handled by the Runner using policy-driven rewind anchors.

This design ensures AEL remains:

- extensible
- maintainable
- reproducible
- contributor friendly
