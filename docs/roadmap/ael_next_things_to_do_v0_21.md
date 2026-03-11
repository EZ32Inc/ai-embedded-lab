# AEL Next Things To Do List v0.21

Status baseline:
- Main architecture completed and stabilized at v0.20
- AEL is now moving from core architecture construction into practical capability expansion and workflow/skills accumulation

## Purpose

This document defines the next practical phase of AEL development after the main architecture has been completed and stabilized.

The goal of this phase is not to continue broad architecture invention.

The goal is to:

- expand practical capability coverage on representative mature boards
- make AEL more immediately useful to a large percentage of users
- validate the architecture through real capability use
- accumulate reusable workflow/skills while building examples
- keep improving the system through actual use rather than isolated abstract refinement

This document should serve as the current next-things-to-do list and near-term execution guide.

---

## Phase Summary

Phase v0.21 focuses on **horizontal capability expansion on representative mature boards**.

The main board families are:

- STM32F series
- ESP32 series
- RP2040 / Raspberry Pi Pico series

The main capability areas are:

- GPIO
- UART
- ADC
- USB

GPIO already has meaningful coverage and serves as the current baseline.

The next expansion focus should be:

1. UART
2. ADC
3. USB

---

## Why This Phase Matters

AEL main architecture is already in a strong and stable state.

The next highest-value step is to make the system more directly useful in common real user scenarios.

If these representative boards and common capability examples become mature and easy to use, then a very large percentage of users should be able to take AEL and immediately run examples that are:

- relevant
- likely to succeed
- easy to extend
- useful as templates for their own work

This phase also serves another major purpose:

AEL should not only build examples.
AEL should also accumulate reusable engineering knowledge while building those examples.

That means the system should capture:

- recurring bring-up workflows
- recurring troubleshooting patterns
- capability-specific verification methods
- board-specific pitfalls
- reusable AI/human guidance

This is one of the major strengths of the AEL approach.

---

## Main Goals

### Goal 1: Expand representative board coverage
Focus on the most representative mature board families:

- STM32F
- ESP32
- RP2040 / Pico

These families should serve as the primary practical coverage set for this phase.

### Goal 2: Expand common capability examples
Build and mature practical examples for:

- UART
- ADC
- USB

GPIO remains the baseline reference capability.

### Goal 3: Create reusable patterns, not one-off demos
Each new example should aim to become:

- a user-facing example
- a reusable verification pattern
- a future reference for AI/Codex
- a source of workflow/skills accumulation

### Goal 4: Improve AEL through use
The system should now be improved mainly by being used in real example-building work.

This means:

- use the existing architecture
- observe what works well
- improve only where practical use reveals real needs
- avoid abstract architecture churn without concrete evidence

### Goal 5: Accumulate workflow/skills during execution
While implementing new board/capability examples, AEL should also capture:

- workflow docs
- troubleshooting skills
- board bring-up patterns
- capability verification patterns

This is a core part of the phase, not optional extra documentation.

---

## Representative Board Families

### 1. STM32F Series
Why:
- highly representative MCU family
- broad user base
- strong relevance for embedded developers
- useful for GPIO/UART/ADC/USB coverage

### 2. ESP32 Series
Why:
- extremely common
- strong practical relevance
- useful for both MCU and connectivity-oriented users
- important for UART/ADC/USB and system-level examples

### 3. RP2040 / Raspberry Pi Pico Series
Why:
- very popular
- easy to access and reproduce
- good for practical demos and cross-platform verification
- useful for user-facing examples and broad adoption

---

## Capability Expansion Priority

### Baseline already present
- GPIO

### Priority 1
- UART

Why:
- highly common
- broadly useful
- relatively straightforward
- strong candidate for reusable verification pattern
- strong user value

### Priority 2
- ADC

Why:
- expands AEL from digital behavior into sampled/value-oriented verification
- introduces new verification and observation patterns
- highly relevant in many real projects

### Priority 3
- USB

Why:
- very valuable and highly visible
- but usually more complex
- better to approach after UART and ADC patterns are more mature

---

## Capability Matrix

Target matrix for this phase:

| Board Family | GPIO | UART | ADC | USB |
|---|---:|---:|---:|---:|
| STM32F | baseline exists | target | target | target |
| ESP32 | baseline exists | target | target | target |
| RP2040 / Pico | baseline exists | target | target | target |

This matrix does not require every cell to become equally advanced immediately.

It is a direction-setting matrix for practical coverage.

---

## Key Working Principle

This phase should not become a “collect examples mechanically” phase.

The main principle is:

> Build examples, validate real usage, and accumulate reusable workflow/skills at the same time.

In other words, the output of each successful capability expansion should include two things:

1. the example / support itself
2. the reusable knowledge generated while building it

---

## Expected Skills / Workflow Accumulation

Examples of skills/workflow notes likely to emerge during this phase include:

- board bring-up workflow for a new mature board
- UART verification workflow
- ADC verification workflow
- USB example bring-up workflow
- common capability troubleshooting workflow
- board-specific issue notes
- pattern for reusing an example across multiple board families

These should be added only when they are grounded in real recurring work.

---

## Recommended Development Pattern For This Phase

Use the established AEL working method:

**architecture → roadmap → tasks → review → update architecture → update roadmap → tasks → review again**

For this phase, that means:

1. use the stabilized main architecture as the baseline
2. define bounded board/capability work items
3. let Codex implement and validate them
4. review actual code/tests/runtime behavior
5. capture useful workflow/skills
6. adjust the next tasks based on practical findings

This phase should be driven by real use, not by speculative redesign.

---

## Recommended Near-Term Sequence

### Batch A
Define the first capability-expansion roadmap/checklist in more concrete terms.

Suggested first focus:
- UART on STM32F
- UART on ESP32
- UART on RP2040/Pico

### Batch B
Implement and validate UART examples on the representative mature boards.

### Batch C
Capture UART-related workflow/skills from real work.

### Batch D
Move to ADC expansion across the same representative board set.

### Batch E
Capture ADC-related workflow/skills.

### Batch F
Move to USB expansion where practical and justified.

### Batch G
Review example maturity, user coverage, and remaining gaps.

---

## What Success Looks Like

This phase is successful if AEL reaches a point where:

- most users can pick a familiar board family and find a working example
- examples are not just demos, but practical templates
- common capability patterns are reusable across board families
- new example creation becomes easier because prior workflow/skills exist
- AEL improves through practical use rather than abstract polishing alone

A stronger success condition is:

- 80% to 90% of typical users can quickly find and run a useful baseline example relevant to their own platform and next step

---

## What To Avoid

### 1. Over-polishing the core without new practical use
The main architecture is already stable enough.
Do not remain stuck in architecture-only refinement.

### 2. Building too many disconnected examples
Examples should contribute to reusable patterns and capability coverage.

### 3. Writing workflow/skills without real experience
Only capture workflow/skills from actual recurring work.

### 4. Expanding too many dimensions at once
Prefer staged expansion:
- first UART
- then ADC
- then USB

### 5. Treating all boards/features as equal priority
Stay focused on the representative board set and the highest-value common capabilities.

---

## Current Conclusion

AEL main architecture is complete and stable.

The next important phase is to use that architecture to expand practical board/capability coverage while accumulating reusable workflow/skills.

This should be the primary direction for v0.21.

---

## Suggested Next Action

Ask Codex to review this v0.21 next-things-to-do document against the current repo and propose:

- corrections if needed
- a first bounded task list
- the best first execution batch for UART expansion on representative mature boards

