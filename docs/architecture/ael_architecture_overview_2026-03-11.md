# AEL Architecture Overview
Date: 2026-03-11

## Purpose

This document is the current repo-level architecture overview for AEL.

It is intended to:
- explain what AEL is at the current repository stage
- summarize the major architecture areas in one place
- distinguish confirmed implementation from interpretation and remaining gaps
- provide a durable reference for future roadmap and batch planning

This is not a session note.

## What AEL Is

AEL is an AI-oriented embedded lab runtime and execution system.

It is designed to give AI agents and humans a structured way to:
- resolves a run from board/test/instrument context
- produces a plan-driven execution flow
- runs build / flash / observe / verify steps
- captures artifacts and evidence
- supports both one-off runs and repeated default verification on real benches

In repo terms, AEL is not just a generic test framework.
It is an execution system for real embedded-lab work:

- resolve hardware and policy context
- bind bench resources and instruments
- execute hardware-facing stages
- preserve evidence and operator-readable summaries
- support repeatable AI/human workflows around that runtime

The current repo is no longer just a simple single-board runner.
It already contains:
- a plan-driven run pipeline
- inventory and explanation surfaces
- workflow archive support
- DUT asset support
- default verification as a suite/task/worker execution model

## Current Phase

Reasonable current phase description:

- Phase 1 core architecture work is largely complete
- the repo is in a consolidation and operational-policy phase

This means:
- the main execution architecture is already real
- the main models are already visible in code and docs
- the next work should mostly be bounded cleanup, policy tightening, compatibility retirement, and workflow/method buildup

## Main Architecture Parts

The current repo is best described as seven main parts, plus one cross-cutting layer.

## 1. Run Resolution and Planning

### Confirmed current state

- CLI entry, inventory, explain-stage, and run-resolution surfaces are real and active.
- AEL already turns board/test/control-instrument context into structured execution inputs.
- Planning is not implicit shell glue; it is represented through run-plan generation and stage explanation.

### Strong / mature parts

- The repo already has a usable planning boundary for both humans and AI-facing workflows.
- Inventory and explain outputs are now materially aligned with canonical runtime objects.

### Still consolidating

- Some older docs/specs still describe earlier plan/runtime assumptions.
- Resolution precedence across board, DUT, and compatibility inputs can still be tightened.

### Main references

- [__main__.py](/nvme1t/work/codex/ai-embedded-lab/ael/__main__.py)
- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [inventory.py](/nvme1t/work/codex/ai-embedded-lab/ael/inventory.py)

## 2. Execution Engine

### Confirmed current state

- AEL already has a plan-driven single-run execution engine.
- Build / load / check / report are real stage boundaries in the current runtime.
- Retry handling, result shaping, and artifact writing are already core runtime behavior.

### Strong / mature parts

- Single-run execution is a strong architectural part of the repo now.
- Result/evidence writing and structured stage execution are already stable enough to build on.

### Still consolidating

- Some runtime internals still carry historical naming and compatibility seams.
- Recovery behavior beyond current bounded policies is still modest.

### Main references

- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- `runner.py`
- adapter registry and step execution paths

## 3. Default Verification Orchestration

### Confirmed current state

- Default verification is now a real subsystem with its own runtime model.
- It already includes:
  - suite / task / worker structure
  - parallel worker execution
  - repeat mode
  - shared-resource locking
  - degraded-instrument policy at the suite level

### Strong / mature parts

- This is one of the most mature parts of the current repo.
- It has both targeted tests and repeated live bench validation behind it.
- It is no longer just a convenience command around the single-run engine.

### Still consolidating

- Broader contention/stress coverage can still expand.
- Some recovery behavior under degraded hardware is intentionally bounded rather than fully generalized.

### Main references

- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)

## 4. Hardware Model and Resource Contract

### Confirmed current state

- This part currently includes:
  - instrument model
  - DUT model
  - board-profile boundary
  - bench/resource/connection model
  - runtime resource identity used for locking and reporting
- Durable references already exist for:
  - [instrument_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/instrument_model.md)
  - [dut_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/dut_model.md)
  - [bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)

### Strong / mature parts

- Canonical runtime/report/archive objects now expose:
  - `selected_dut`
  - `selected_board_profile`
  - `selected_bench_resources`
- Control-instrument-first migration is well established on active surfaces.
- Resource identity is now visible enough to support both operator reasoning and tooling.

### Still consolidating

- Runtime execution is still more board-profile-driven than fully DUT-driven.
- Internal compatibility seams remain, especially around older `probe*` naming and helper paths.
- Bench/resource semantics are strongest around default verification, not every future mode.

### Reasonable interpretation

- This combined hardware/resource part fits the repo better than treating instrument, DUT, and bench as totally separate top-level systems.
- The most important next work is bounded tightening of these boundaries, not broad conceptual redesign.

## 5. Adapters and Capability Surfaces

### Confirmed current state

- Build, flash, observe, verify, and preflight behavior already lives in adapter-oriented code paths.
- Capability surfaces are now increasingly visible in structured control-instrument and instrument metadata.

### Strong / mature parts

- AEL already has a real variability layer for hardware- and tool-specific behavior.
- The core runtime does not need separate architecture per board family; it delegates much of that variability here.

### Still consolidating

- Some older adapter APIs still expose historical naming or capability assumptions.
- There is still room to reduce special-case logic leaking back upward into runtime code.

### Main references

- `ael/adapters/*`
- adapter registry
- capability metadata and instrument metadata modules

## 6. Evidence, Diagnostics, Reporting, and Archive

### Confirmed current state

- Early meter failures now emit structured observations and evidence.
- Verify-stage failures now preserve more detail at suite-level results.
- Operator-facing summaries now expose:
  - `failure_class`
  - `instrument_condition`
  - `failure_scope`
  - `verify_substage`
  - compact bench observations
- A bounded degraded-instrument policy now exists:
  - fail fast for clearly unreachable instruments
  - retry once for transient transport/API degradation
  - do not auto-retry verify-stage instrument failures
- Durable policy doc exists in [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md).
- Workflow archive support is also a real part of the current reporting contract.

### Strong / mature parts

- Failure reporting is materially better than earlier in the repo history.
- Bench-side degradation is now less likely to be mistaken for an execution-model defect.
- Repeat-mode results now expose degraded worker health more explicitly.
- Reporting is not just output formatting in AEL; it is part of the runtime contract.

### Still consolidating

- The evidence taxonomy is stronger, but not complete.
- ESP32-C6 remains a live unstable-bench example, especially around Wi‑Fi/meter behavior.
- There is still room for better verify-stage classification and richer comparative evidence when it proves necessary.

### Reasonable interpretation

- This area has moved from weak to useful.
- The next work should be selective, driven by real remaining ambiguity, not speculative observability growth.

## 7. Operational Knowledge / Workflow Layer

### Confirmed current state

- `docs/skills/README.md` exists and is being used as the style guide.
- Several reusable skills/docs now exist around real repo work:
  - repeat mode
  - probe fallback policy
  - worker resource locking
  - ESP32-C6 intermittent bench failure
  - degraded instrument handling
- Workflow archive support exists in code.

### Strong / mature parts

- The repo has crossed the threshold where method knowledge is being preserved, not only inferred from sessions.
- This is a scaling mechanism for future AI/human work, not just “documentation”.
- It already improves repeatability of review, diagnosis, and future batch execution.

### Still consolidating

- The method/skills layer is still small compared to what the architecture now supports.
- There is not yet a broad operator/developer playbook covering all major recurring tasks.
- The workflow layer is durable enough to build on, but still early.

### Reasonable interpretation

- Phase 2 should expand this area deliberately, because the repo is now complex enough that method guidance pays off quickly.

## Cross-Cutting Layer: Compatibility and Migration

Compatibility and migration should not be treated as a main architecture part.
It cuts across the whole system.

Current examples:

- `probe*` to `control_instrument*`
- older flat board/probe payloads to canonical runtime boundary objects
- older plan/report/archive examples that still need compatibility framing

Current state:

- compatibility is much narrower than before
- it is now explicit in many outputs
- it is still unfinished

Guiding rule:

- canonical model first
- compatibility second
- gradual retirement later

## Areas That Are Currently Strong

Most mature today:

1. Default verification orchestration
2. Run execution and reporting surfaces
3. Hardware/resource boundary visibility on active paths
4. Operator-facing degraded-instrument reporting and policy

These are now strong enough to serve as stable foundations rather than open architecture questions.

## Areas Still Partially Consolidated

Most clearly still consolidating:

1. Full compatibility retirement of legacy `probe*` internals and examples
2. Deeper DUT runtime boundary tightening beyond current report objects
3. Broader bench/resource contract cleanup beyond default-verification-focused cases
4. Operational knowledge/workflow coverage for recurring work

## Most Important Remaining Architectural Gaps

The most important gaps are now bounded and practical:

1. Compatibility retirement
- keep shrinking visible and internal legacy `probe*` dependencies where safe

2. DUT runtime boundary tightening
- decide what should become a true runtime DUT concern versus board-policy concern

3. Bench/resource contract hardening
- keep making bound resources, drift, and degraded bench behavior easy to understand

4. Recovery policy beyond current degraded-instrument defaults
- current degraded-instrument handling is intentionally bounded
- future real recovery actions are still mostly open

5. Workflow/skills expansion
- the repo now needs more durable operator/developer guidance to match its architecture maturity

## Working Interpretation of Repo State

The repo is no longer in early architecture formation.

It is better described as:

- architecture defined
- major runtime model implemented
- major migration direction chosen
- compatibility and policy consolidation still underway

That means the right Phase 2 approach is:

- bounded cleanup
- explicit policy
- compatibility retirement
- method buildup
- no broad rewrites unless a specific boundary proves too costly to keep

## Related Reference Docs

- [instrument_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/instrument_model.md)
- [dut_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/dut_model.md)
- [bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)
- [default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)
- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
- [control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)
- [skills/README.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/README.md)
