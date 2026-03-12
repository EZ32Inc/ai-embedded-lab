# AEL Phase 2 Roadmap
Date: 2026-03-11

## Purpose

This roadmap defines the next phase of AEL work after the main Phase 1 architecture foundation was established.

Phase 2 is not about inventing the core model again.
It is about:

- consolidation
- operational policy
- compatibility retirement
- workflow / skills buildup
- bounded model cleanup

This roadmap is intended to be executable by humans and Codex against the current repository state.

It follows the current architecture framing in:
- [ael_architecture_overview_2026-03-11.md](/nvme1t/work/codex/ai-embedded-lab/docs/architecture/ael_architecture_overview_2026-03-11.md)

## Current State Summary

Based on the current repository:

- the default verification execution model is already real and mature enough to build on
- control-instrument-first migration is materially established on active runtime/report/archive paths
- canonical runtime boundary objects now exist:
  - `selected_dut`
  - `selected_board_profile`
  - `selected_bench_resources`
- degraded external instrument behavior now has an explicit default policy
- actual run paths now include a small bounded readiness tolerance for transient meter startup latency
- visible compatibility retirement has progressed further on active CLI/help/runtime surfaces
- runtime summaries now expose `dut_runtime_binding` and `board_profile_role` more explicitly
- workflow/skills documentation is now materially established as an execution-scaling layer for humans and AI agents

So Phase 2 should assume:

- core architecture is largely in place
- broad rewrites are not the default answer
- the next value is in tightening boundaries, reducing compatibility debt, and improving durable operational guidance

## Current Closeout Status

As of the current repo state, Phase 2 is substantially complete in bounded form.

That closeout includes:

- the bounded Local Instrument Interface refactor from Phase 1 is complete
- the three default-verification paths now route their required instrument-touching runtime interactions through the Local Instrument Interface
- `verify-default` remains stable within the known bench-side ESP32-C6 meter-instability envelope

What this means operationally:

- Phase 2 should now be treated as closed for new architecture-expansion work
- follow-on work should open a new execution-facing phase instead of extending Phase 2 by momentum

## Working Principles

Phase 2 should follow these rules:

1. Favor bounded consolidation passes over big rewrites.
2. Canonical model first, compatibility second, gradual retirement later.
3. Prefer explicit policy over implicit behavior.
4. Treat unstable bench/instrument behavior as a first-class operational case.
5. Keep execution-model confidence high through targeted tests and live validation where appropriate.
6. Expand durable workflow/method docs as a parallel track, not a later afterthought.

## Priority Areas

## 1. Compatibility Retirement

### Why it matters

The canonical model is now clearer than the compatibility layer.
Leaving too much legacy surface in place risks future confusion and accidental backsliding.

### Phase 2 intent

- continue shrinking visible and internal `probe*` compatibility where safe
- keep compatibility explicit instead of co-equal with canonical structures
- avoid large breakage-oriented cleanup
- prefer user-visible cleanup first, then older examples/specs, then deeper internal seams

### Deliverables

- narrower visible `probe*` surface
- clearer compatibility/deprecation boundary
- updated compatibility note and examples
- legacy `--probe` and older payload aliases limited to explicit compatibility contexts
- remaining `probe*` usage concentrated mostly in compatibility objects, older examples/specs, and internal helper seams

## 2. Degraded Instrument / Degraded Bench Policy

### Why it matters

The repo now has strong classification/reporting policy already, but deeper recovery policy is still intentionally bounded.

### Phase 2 intent

- keep the current classification/reporting policy stable
- decide whether and where deeper recovery actions belong
- avoid conflating bench degradation with core execution defects

### Deliverables

- stable degraded-instrument classification/reporting guidance
- stable handling of short transient bench-readiness spikes without broad recovery churn
- any bounded recovery additions justified by real bench need
- stronger repeat-mode/operator guidance for unstable external instruments

## 3. DUT Runtime Boundary Tightening

### Why it matters

The repo now reports DUT and board profile separately, but execution is still largely board-profile-centric.

### Phase 2 intent

- tighten DUT/runtime boundaries without broad runtime redesign
- clarify where DUT identity should matter in resolution, reporting, and method guidance
- keep board profile focused on runtime/tool policy

### Deliverables

- clearer DUT selection/runtime rules
- fewer ambiguous board-vs-DUT semantics
- updated docs and targeted runtime/output cleanup where needed
- active summaries and describe/explain paths that make DUT identity and board-policy role easier to distinguish

## 4. Bench / Resource Contract Tightening

### Why it matters

Bench/resource behavior is operationally important now, especially for parallel verification and unstable instruments.

### Phase 2 intent

- keep improving resource identity clarity
- ensure selected bench resources, lock identity, and reported setup stay aligned
- expand only where real bench needs justify more complexity

### Deliverables

- tighter resource/connection contracts
- clearer drift/comparison guidance
- better operator understanding of shared-resource and degraded-bench behavior
- clearer operator separation between bench-resource drift and degraded-instrument failure

## 5. Workflow / Skills / Method Buildup

### Why it matters

The repo now contains enough real architecture and operational policy that undocumented method becomes a scaling problem.

### Phase 2 intent

- expand the skill/workflow layer around recurring operational tasks
- preserve reusable method knowledge faster than it is lost
- support both humans and Codex with durable guidance

### Deliverables

- more durable skill documents
- stronger operator/developer playbooks
- clearer architecture-to-method linkage
- explicit guidance for recurring Phase 2 distinctions such as:
  - late verify failure interpretation
  - control-instrument compatibility boundary
  - bench drift vs degraded instrument
  - roadmap-driven AI development

## Suggested Batch Sequence

## Batch Group A: Compatibility Cleanup

1. Audit remaining visible `probe*` references in active docs/examples/help.
2. Demote or rewrite them where users would still be confused.
3. Keep compatibility only where it is intentionally needed.
4. Treat older active docs/examples as a higher priority than deep internal helper renames.

## Batch Group B: Degraded-Instrument Policy Hardening

1. Observe the current policy against real failures.
2. Add only bounded policy/refinement where repeated ambiguity remains.
3. Consider recovery actions only if the bench supports them and the value is clear.

## Batch Group C: DUT Runtime Cleanup

1. Audit where runtime still behaves too much like “board only”.
2. Tighten DUT/board profile responsibility boundaries.
3. Prefer reporting/resolution cleanup before deep runtime refactor.

## Batch Group D: Bench/Resource Contract Cleanup

1. Tighten resource identity and drift semantics.
2. Keep lock identity, selected bench resources, and current/LKG output aligned.
3. Expand resource classes only for real new contention needs.
4. Avoid changing stable comparison fields unless operator value clearly improves.

## Batch Group E: Workflow/Skills Expansion

1. Add durable docs for recurring operational policy and review patterns.
2. Focus on real repeated work, not abstract completeness.
3. Keep the skills layer aligned with the actual repo, not older assumptions.

These batch groups should be treated as partially parallel tracks:

- compatibility retirement and workflow/skills buildup can proceed alongside each other
- degraded-bench policy observation can also run in parallel with bounded DUT/runtime cleanup

## Deliverables for Phase 2

The main expected deliverables are:

- a narrower and clearer compatibility boundary
- stable degraded-instrument and degraded-bench policy guidance
- tighter DUT runtime boundaries
- tighter bench/resource contracts
- stronger workflow/skills coverage for operators and Codex
- updated durable architecture docs as the canonical repo references
- a clearer deprecation boundary for remaining visible legacy control-instrument compatibility

## Phase 2 Exit Criteria

Phase 2 should be considered substantially complete when:

- the active user-facing/runtime-facing contract is overwhelmingly canonical rather than compatibility-led
- degraded-instrument classification/reporting is stable and deeper recovery policy is clearly bounded and documented
- DUT / board-profile / bench-resource runtime boundaries are clearer and less ambiguous than today
- bench/resource contracts are easier to compare, reason about, and explain
- bench/resource comparison is operator-friendly, with stable compact digests and clear LKG drift reporting
- workflow/skills coverage is strong enough to support repeated AI/human work without relying mainly on session memory

## What Phase 2 Should Avoid

Phase 2 should avoid:

- broad renaming campaigns without compatibility planning
- deep rewrites when bounded cleanup is sufficient
- speculative generalization not justified by current repo needs
- overbuilding diagnostics without a concrete ambiguity to solve

## How to Evaluate Progress

Phase 2 is going well if:

- canonical runtime/model terminology becomes easier to follow, not harder
- fewer outputs still expose confusing legacy concepts as primary
- degraded bench behavior is easier to classify and explain
- DUT / board / bench boundaries are easier to reason about
- the skills/workflow layer grows in proportion to the repo’s real operational complexity

## Immediate Recommended Starting Point

The best next Phase 2 starting sequence is:

1. continue compatibility retirement on remaining active older docs/examples and compatibility-led visible surfaces
2. observe degraded-instrument policy against real failures before expanding deeper recovery behavior
   current note: direct live bench evidence matters more than restricted/sandboxed loop output for this review
3. keep tightening bench/resource comparison and drift semantics where operator value is clear
4. continue bounded DUT/runtime cleanup only where board-profile-driven behavior is still too ambiguous in active outputs
5. keep expanding workflow/skills in parallel around recurring Phase 2 review and operations work

Current practical emphasis:
- doc/example cleanup first
- contract churn only when it buys real operator clarity
- let real bench failures drive any further observability expansion

Current practical checkpoint:
- most remaining compatibility debt is now internal or explicitly compatibility-scoped
- Phase 2 should avoid turning that into a broad rename campaign
- the next useful work should continue to be checkpoint-driven rather than migration-for-its-own-sake
