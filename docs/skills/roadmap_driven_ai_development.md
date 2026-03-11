# Skill: Roadmap-Driven AI Development

## Purpose

This document captures a practical development method that has proven effective in AEL:

- discuss and clarify the overall architecture first
- generate a roadmap from that architecture
- let AI/Codex turn the roadmap into concrete tasks and implementation
- review actual code, tests, docs, and runtime behavior
- update the architecture based on what the system has really become
- update the roadmap based on the updated architecture
- continue with the next task batch

This is not a rigid top-down planning method.
It is a guided, iterative, architecture-driven, reality-based AI development workflow.

---

## Core Idea

In this workflow, architecture comes before roadmap, and roadmap comes before task batches.

The architecture defines:

- the major parts of the system
- the intended boundaries between subsystems
- the main direction of growth
- the important abstractions and contracts

The roadmap then translates the current architecture into:

- near-term priorities
- bounded batches
- migration direction
- practical next steps

The roadmap is not a fixed construction drawing.
It is better understood as:

- a direction-setting document
- an architecture-derived action guide
- a priority guide
- a coordination surface between human judgment and AI execution

AI/Codex is not expected to follow the roadmap mechanically.
Instead, it should use the roadmap as a structured guide while adapting to:

- actual repository state
- actual code paths
- actual tests
- actual live bench behavior
- newly discovered architectural reality

This allows the system to grow in a way that is less rigid and more correct.

---

## Why Architecture Matters First

Roadmaps are only useful if they are grounded in a reasonable architecture view.

If the architecture framing is weak or outdated, then the roadmap may still help locally, but it will eventually drift from reality.

In AEL, the effective pattern is:

1. discuss the overall architecture
2. define the current main parts and boundaries of the system
3. generate the roadmap from that architecture
4. execute bounded task batches
5. review what the codebase actually became
6. update the architecture view if needed
7. update the roadmap based on the updated architecture
8. continue the next batch

This means architecture is not static.
It is reviewed and refined as the real system grows.

---

## Why This Works

Traditional human-only development often suffers from:

- large perceived workload
- delay and hesitation before implementation
- repeated re-interpretation of goals
- inconsistency between design intent and actual code
- documentation lagging behind implementation
- architecture drift without explicit review

This AI-assisted workflow reduces those costs by making development more continuous and more reviewable.

The key benefits are:

- architecture gives overall shape
- roadmap gives clear direction
- AI can immediately turn direction into action
- review happens against code and runtime reality
- architecture is updated instead of treated as sacred
- roadmap is updated instead of treated as sacred
- the system can evolve without becoming chaotic
- method and knowledge can be captured as reusable workflow/skills

---

## Effective Working Pattern

The currently effective working pattern is:

**architecture → roadmap → tasks → review → update architecture → update roadmap → tasks → review again**

This should be treated as a real working method, not a temporary habit.

Expanded form:

1. discuss and tighten the current architecture
2. write or refine the roadmap derived from that architecture
3. let Codex execute the next task batch
4. review actual code, tests, docs, and runtime behavior
5. compare results against architecture intent
6. update the architecture if the real system has grown differently or more clearly
7. update roadmap/design docs based on the updated architecture
8. launch the next batch
9. repeat

This loop allows architecture and implementation to co-evolve.

---

## Recommended Loop

### Step 1: Review or define architecture
The human and AI first clarify the overall architecture.

This includes:

- what the main parts of the system are
- where subsystem boundaries should be
- which models are canonical
- which areas are mature
- which areas are transitional
- which cross-cutting concerns exist

Important rule:

Do not force the system into an outdated architecture model.
Review the current repository state and describe the architecture that best matches reality.

### Step 2: Generate or refine roadmap
The roadmap should be generated from the current architecture view.

The roadmap should define:

- current priorities
- bounded next steps
- migration direction
- what should be stabilized
- what should be avoided
- what should count as progress

The roadmap should be clear, but not overly rigid.

### Step 3: Convert roadmap into task batches
Codex should turn roadmap priorities into bounded batches.

Each batch should be:

- concrete
- reviewable
- small enough to validate
- aligned with current repo reality

### Step 4: Execute
Codex performs implementation, testing, documentation, and cleanup.

This may include:

- code changes
- tests
- doc updates
- live validation
- migration cleanup
- policy clarification

### Step 5: Review reality
After each meaningful batch, review:

- actual code behavior
- test results
- runtime output
- live bench behavior if relevant
- whether the repo still matches the architecture story

This step is essential.

### Step 6: Update architecture first
If the system has grown in a better or more realistic direction than originally expected, update the architecture overview first.

This includes reviewing:

- whether the architecture naming is still reasonable
- whether the subsystem boundaries are still correct
- whether new major parts have emerged
- whether old categories no longer fit reality

Do not force reality back into an outdated architecture.

### Step 7: Update roadmap second
After the architecture is updated, update the roadmap.

The roadmap should now reflect:

- the updated architecture
- completed work
- remaining gaps
- better next priorities
- more accurate batch structure

### Step 8: Start next batch
Use the updated architecture and updated roadmap as the basis for the next batch.

Then repeat the cycle.

---

## Operating Principle

The architecture is a guide, not a prison.
The roadmap is a guide, not a prison.

Good AI-assisted architecture growth is not:

- design everything once
- force code to match the original sketch forever

Good AI-assisted architecture growth is:

- define goals and boundaries
- clarify current architecture
- derive roadmap from architecture
- implement in bounded steps
- review actual results
- let architecture tighten around reality
- update the roadmap accordingly
- continue

---

## Role of the Human

The human should primarily focus on:

- defining overall direction
- checking architectural clarity
- deciding priorities
- judging whether reality matches intent
- identifying when architecture/docs/roadmap need updating
- deciding what should be stabilized into policy or workflow

The human does **not** need to manually write most implementation details.

The human is primarily responsible for:

- meaning
- architecture
- judgment
- validation criteria

---

## Role of AI / Codex

AI/Codex should primarily focus on:

- reviewing the current codebase against architecture intent
- helping redefine the architecture when the current framing no longer fits
- translating architecture and roadmap direction into executable batches
- implementing bounded changes
- updating tests
- updating docs
- identifying mismatches, debt, or next-step opportunities
- helping the system grow toward a cleaner real architecture

AI should not be treated as a rigid code typist.
It should be used as an implementation and review engine operating within architecture-defined and roadmap-defined boundaries.

---

## What Makes This Better Than Traditional Development

This method can outperform traditional development because:

- architecture stays under active review
- large work is decomposed quickly
- delay is reduced
- implementation can proceed continuously
- review happens earlier and more often
- docs and code can evolve together
- architecture is allowed to become more correct over time
- quality is often better because iteration is tighter and more frequent

A large work item that once felt like months of manual engineering may become days of guided AI-driven progress.

---

## Important Rules

### 1. Do not assume the first architecture is final
The first architecture framing may be useful, but incomplete.

### 2. Do not assume the first roadmap is final
A roadmap may be directionally correct while still incomplete or partially inaccurate.

### 3. Update architecture before updating roadmap
If reality has shifted, architecture should be reviewed first, then roadmap.

### 4. Let the real system teach the architecture
The architecture should be refined from actual repo/code/runtime reality, not just original imagination.

This is a strength, not a weakness.

---

## Signs This Workflow Is Working

You know this workflow is working when:

- Codex can take the roadmap and make meaningful forward progress without constant re-explanation
- architecture docs become more accurate over time
- implementation and documentation stay closer together
- the system “grows” into a better structure than originally imagined
- review mostly happens at the architecture, behavior, and contract level rather than through manual line-by-line coding
- progress is fast without becoming chaotic

---

## Risks to Avoid

### 1. Overly rigid architecture
If the architecture is treated as untouchable, the system may be forced into the wrong shape.

### 2. Overly rigid roadmap
If the roadmap is treated as untouchable, implementation may drift from reality while pretending to stay aligned.

### 3. No architecture review
If architecture is not reviewed, roadmap may slowly become disconnected from the real repo.

### 4. No roadmap
If there is no roadmap, AI may still make local progress but the system can drift.

### 5. Large uncontrolled rewrites
Big rewrites without bounded task batches reduce clarity and increase risk.

### 6. Skipping review
If review is skipped, architecture, roadmap, and implementation can silently diverge.

### 7. Updating code without updating architecture/docs
This weakens the method layer and reduces future scaling value.

---

## Recommended Use in AEL

This method is especially effective for AEL because AEL combines:

- architecture evolution
- real hardware constraints
- live bench validation
- compatibility migration
- policy decisions
- reusable engineering workflows

AEL benefits from a method where:

- architecture sets the overall structure
- roadmap sets the current direction
- tasks are generated and executed quickly
- live reality feeds back into design
- architecture and roadmap are both updated continuously
- docs and skills are updated continuously

---

## Suggested Output Pattern For Future Work

For major ongoing work, prefer this cycle:

1. review or tighten architecture
2. create or tighten roadmap
3. run next task batch
4. review code/tests/runtime behavior
5. update architecture
6. update roadmap
7. run next task batch
8. review again

Short form:

**architecture → roadmap → tasks → review → update architecture → update roadmap → tasks → review again**

---

## Relationship to Skills / Workflow Docs

This document should be considered a reusable workflow skill.

It is not tied to only one technical subsystem.

It captures a general AEL working method that can be reused across:

- architecture consolidation
- migration work
- runtime cleanup
- diagnostics improvement
- policy refinement
- future subsystem expansion

---

## Notes

This workflow has already shown that AI-assisted development is not just “faster coding.”

It is a different engineering mode:

- less delay
- less manual detail burden
- tighter review loops
- better architecture/doc/code alignment
- more organic but still controlled system growth

The architecture gives the overall shape.
The roadmap gives the current direction.
The task batches are the execution units.
The review loop is what keeps the system correct.
