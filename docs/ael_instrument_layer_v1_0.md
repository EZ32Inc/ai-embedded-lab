# AEL Instrument Layer v1.0

Date: 2026-03-18
Status: Active

## Purpose

This is the single entry document for the AEL instrument layer.

Use this document first when:

- designing or reviewing instrument architecture
- packaging ESP32-JTAG as the reference instrument
- aligning other instruments to the Instrument Action Model (IAM)
- deciding what "done" means for the instrument layer

This document is intentionally short. It defines the overall shape and points to the three execution attachments:

- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)
- [esp32_jtag_backend_skeleton_v0_1.md](./esp32_jtag_backend_skeleton_v0_1.md)

Related IAM base docs:

- [docs/specs/instrument_action_model_v0_1.md](./specs/instrument_action_model_v0_1.md)
- [docs/specs/instrument_action_examples_v0_1.md](./specs/instrument_action_examples_v0_1.md)
- [docs/specs/instrument_action_implementation_plan_v0_1.md](./specs/instrument_action_implementation_plan_v0_1.md)

## Overview

AEL instrument layer is the interface between AI and the physical world.

The stack is:

```text
AI Agent
  -> IAM
  -> Instrument Backend
  -> Transport
  -> Physical Device
  -> DUT / Signal / Bench Reality
```

The core rule is:

> Do not adapt AI to tools. Adapt tools to AI.

That means the instrument layer must expose:

- a small standard action surface
- deterministic behavior
- structured result and error shapes
- clear backend boundaries

## Core Decision

ESP32-JTAG is the reference implementation for the next phase.

This is not just another backend. It is the first full IAM-aligned standard implementation used to:

- prove the IAM is practical
- lock the expected backend structure
- define the result/error contract in code
- create the template that ST-Link, USB-UART, and later instruments should follow

## Instrument Layer Principles

### 1. Action-first

The primary question is not "what kind of device is this?"

The primary question is:

> What standard actions can this instrument perform for this DUT?

### 2. AI-first

The interface must be easy for an AI agent to:

- choose
- call
- inspect
- recover from failure

### 3. Structured outputs only

Success and failure must both be structured. Raw backend logs are supporting artifacts, not the primary output contract.

### 4. Backend freedom, contract stability

Internal backend code may vary by transport and hardware.
The AI-facing action names, result shape, and behavior rules should not drift.

### 5. Deterministic workflows

Common sequences such as `flash -> reset -> measure` and `attach -> halt -> read_memory` should be predictable and repeatable.

## IAM Core Rules

### Standard action set

Current IAM v0.1 action set:

- `flash`
- `reset`
- `uart_read`
- `uart_wait_for`
- `gpio_measure`
- `voltage_read`
- `debug_halt`
- `debug_read_memory`

ESP32-JTAG reference scope should start with:

- `flash`
- `reset`
- `gpio_measure`

Planned next additions:

- `debug_halt`
- `debug_read_memory`

### Success result shape

```json
{
  "status": "success",
  "action": "flash",
  "data": {},
  "logs": []
}
```

### Failure result shape

```json
{
  "status": "failure",
  "action": "flash",
  "error": {
    "code": "programming_failure",
    "message": "flash failed",
    "details": {}
  }
}
```

### Non-negotiable rules

- No custom action names for standard behaviors.
- No backend-specific free-form result shape.
- No unstructured failure as the primary output.
- Input validation must fail clearly.
- Unsupported actions must fail clearly.

## Reference Implementation: ESP32-JTAG

ESP32-JTAG should define the reference pattern for:

- backend structure
- transport boundary
- action handlers
- capability declaration
- error normalization
- validation plan

Reference-ready means:

- action names match IAM
- supported request fields are explicit
- success and failure shapes are normalized
- smoke and failure-path validation are both defined
- the implementation is understandable enough to serve as the template for future instruments

## Implementation Pattern

Expected separation:

- `backend`: dispatch and normalization
- `transport`: communication with the device
- `actions`: per-action validation and result mapping
- `errors`: typed backend exceptions and error-code mapping
- `capability`: declared support surface

The backend should not absorb all logic into one file.
The transport should not decide IAM semantics.
Action modules should not own transport setup.

See:

- [esp32_jtag_backend_skeleton_v0_1.md](./esp32_jtag_backend_skeleton_v0_1.md)

## Validation Strategy

Validation is part of the design, not post-hoc testing.

Required validation layers:

1. smoke path
2. repeated stability path
3. failure contract path
4. future AI-usage path

The goal is not only to prove that ESP32-JTAG works.
The goal is to prove that the IAM contract works on a real, multi-function instrument.

See:

- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)

## Migration Strategy

Alignment order:

1. ESP32-JTAG as reference implementation
2. ST-Link aligned to the same action/result/error conventions
3. USB-UART aligned where applicable
4. future instruments added by following the same authoring shape

Suggested maturity levels:

- `L0`: legacy, no IAM alignment
- `L1`: partial action alignment
- `L2`: IAM-aligned backend
- `L3`: reference-quality implementation

Current intended positioning:

| Instrument | Target Level | Notes |
|---|---|---|
| ESP32-JTAG | L3 | reference implementation |
| ST-Link | L2 | align after reference is stable |
| USB-UART bridge | L2 | align serial action subset |

## What This Means For AEL

If this document is followed, the instrument layer stops being a collection of ad hoc tool paths.

It becomes:

- a stable AI-facing platform surface
- a reusable implementation template
- a reliable basis for future instrument growth

This is the transition from "instrument support" to "instrument platform."

## Next Step

Immediate focus:

1. define the ESP32-JTAG action mapping
2. define the validation plan
3. lock the backend skeleton
4. implement against those three attachments

Use these attachments next:

- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)
- [esp32_jtag_backend_skeleton_v0_1.md](./esp32_jtag_backend_skeleton_v0_1.md)

