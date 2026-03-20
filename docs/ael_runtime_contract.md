# AEL Runtime Contract

**Date:** 2026-03-20
**Status:** Draft Execution Plan
**Drafted by:** Andrew Li

## AI <-> System Interaction Specification

---

## 1. Purpose

This document defines how AI interacts with AEL at runtime.

It specifies:

- how goals are expressed
- how actions are executed
- how results are returned
- how iteration proceeds

This is a machine-oriented contract.

---

## 2. Core Model

All interactions follow a loop:

`Goal -> Plan -> Action -> Observation -> Evaluation -> Next Step`

AI is responsible for driving this loop.

---

## 3. Goal Definition

A goal must be:

- explicit
- testable
- verifiable

### Example

```json
{
  "goal": "Verify GPIO toggling on PA5 at 1kHz",
  "constraints": {
    "board": "stm32f411",
    "interface": "stlink"
  }
}
```

---

## 4. Plan Representation

A plan is a sequence of actions.

Each step should:

- reference a defined action
- specify required inputs
- define an expected outcome when useful

### Example

```json
{
  "plan": [
    {"action": "generate_firmware", "params": {}},
    {"action": "flash", "params": {}},
    {"action": "measure_signal", "params": {}}
  ]
}
```

---

## 5. Action Interface

All operations must be exposed as structured actions.

Each action must define:

- name
- inputs
- execution behavior
- output schema

### Example

```json
{
  "action": "flash",
  "inputs": {
    "firmware_path": "string",
    "interface": "stlink"
  },
  "output": {
    "status": "success | failure",
    "log": "string"
  }
}
```

---

## 6. Execution Semantics

- Actions are executed sequentially unless specified otherwise
- Each action produces a structured result
- Execution must not rely on implicit human interpretation

---

## 7. Observation Model

All outputs must be structured.

Required properties:

- machine-readable
- deterministic where possible
- comparable across runs

### Example

```json
{
  "observation": {
    "signal_frequency": 998,
    "expected_frequency": 1000,
    "tolerance": 50,
    "status": "pass"
  }
}
```

---

## 8. Evaluation

AI must evaluate results against the goal.

Evaluation types:

- pass / fail
- metric comparison
- constraint satisfaction

### Example

```json
{
  "evaluation": {
    "result": "fail",
    "reason": "frequency out of tolerance"
  }
}
```

---

## 9. Iteration

Iteration is mandatory.

AI must:

- detect failure
- adjust plan or parameters
- re-execute

Allowed adjustments:

- modify firmware
- change parameters
- switch execution mode
- refine measurement

---

## 10. Multi-Modal Execution

Execution may occur in:

- simulation
- emulation
- real hardware

AI may choose execution mode based on:

- cost
- speed
- fidelity

### Example Strategy

```json
{
  "strategy": [
    "simulate first",
    "emulate for validation",
    "hardware for final verification"
  ]
}
```

---

## 11. Orchestration

AI may coordinate multiple systems.

This includes:

- switching execution environments
- combining results
- managing dependencies

---

## 12. Failure Handling

Failure is expected.

The system must:

- return structured errors
- preserve context
- allow retry

### Example

```json
{
  "error": {
    "type": "flash_failure",
    "reason": "connection lost"
  }
}
```

---

## 13. Reproducibility

Each run must include:

- input parameters
- actions executed
- observations
- results

This enables:

- replay
- comparison
- debugging

Each execution should also produce a trace containing:

- goal
- plan
- actions
- observations
- evaluations
- iterations

This trace is the primary artifact of AEL.

---

## 14. State Management

AI may maintain state across iterations.

State includes:

- previous attempts
- parameter changes
- observed patterns

---

## 15. Design Constraints

The system must ensure:

- no hidden side effects
- no ambiguous outputs
- no reliance on manual steps

---

## 16. Execution Priority

When designing features, prioritize:

- AI executability
- structured outputs
- reproducibility

---

## Final Statement

AEL is not an interactive tool.

It is an execution system.

AI does not assist users.

AI operates the system.
