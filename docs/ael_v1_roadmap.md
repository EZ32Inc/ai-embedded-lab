# AEL v1.0 Roadmap

**Date:** 2026-03-20
**Status:** Draft Execution Plan
**Drafted by:** Andrew Li

---

## Phase 1: Capability Layer

**Priority:** Critical

### Goal

Introduce AI-native hardware abstraction.

### Tasks

- [ ] Define a minimal capability API
- [ ] Add `observe_signal(pin)`
- [ ] Add `generate_signal(pin, pattern)`
- [ ] Add `measure_timing(event)`
- [ ] Map existing instruments to capabilities
- [ ] Refactor GPIO and UART usage into the capability layer

---

## Phase 2: Structured Run Record

### Goal

Standardize the execution trace.

### Output Structure

- input
- actions
- observations
- result
- metadata

### Tasks

- [ ] Define a JSON schema
- [ ] Capture all runs
- [ ] Store runs for replay and analysis

---

## Phase 3: Experiment Engine

### Goal

Enable basic multi-run experimentation.

### Features

- repeat N times
- parameter variation
- result comparison

### Tasks

- [ ] Implement repeat execution
- [ ] Add parameter injection
- [ ] Add comparison logic

---

## Phase 4: Observation Upgrade

### Goal

Move beyond logs.

### Tasks

- [ ] Add structured UART parsing
- [ ] Add timing extraction
- [ ] Add signal pattern detection

---

## Phase 5: Memory System

### Goal

Persist experience.

### Store

- failures
- fixes
- board quirks
- instrument behavior

---

## Phase 6: Multi-AI Collaboration

### Goal

Enable role-based AI workflows.

### Example

- Codex -> implementation
- Claude -> validation
- GPT -> strategy

---

## Phase 7: Full Autonomous Mode

### Goal

Support a workflow where the user can say:

> verify this board

and the system:

- generates firmware
- runs tests
- fixes issues
- outputs a conclusion

---

## Final Milestone

> AI completes embedded validation without human intervention.
