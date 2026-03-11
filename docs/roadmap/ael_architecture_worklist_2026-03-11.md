# AEL Architecture Roadmap / Worklist
Date: 2026-03-11

## Purpose

This document summarizes the most important architecture and engineering work currently identified for AEL.

It is intended to:
- provide a stable reference for near-term technical priorities
- help align future design and implementation work
- guide Codex review against the current repository state
- clarify which parts are urgent, which are foundational, and which are next-stage work

This is not a session log.
It is a forward-looking architecture worklist.

---

## Current Situation

AEL has recently made meaningful progress in its default verification execution model, including:
- suite / task / worker structure
- parallel execution for default verification
- worker-safe logging
- resource locking
- clarified repeated-run behavior
- improved probe fallback policy behavior
- first-pass structured meter reachability observations and early failure evidence

This is an important step forward.

At the same time, several larger architectural areas are now becoming more important:
- instrument abstraction
- DUT abstraction
- bench/resource modeling
- observability and diagnostics
- reusable workflow / skills documentation
- stronger validation of worker / task / parallel behavior

The next phase should focus on consolidating these foundations.

---

## Priority Overview

### First-tier priorities
1. Consolidate the default verification execution model
2. Establish lightweight workflow / skills documentation
3. Improve observability for intermittent bench failures, especially ESP32-C6

### Second-tier priorities
4. Define a unified instrument model and network interface
5. Define a unified DUT model and interface
6. Clarify connection / resource / bench modeling

### Third-tier priorities
7. Improve reusable board bring-up and verification patterns
8. Expand diagnostics and reporting structure
9. Strengthen stress and regression validation

---

## 1. Default Verification Execution Model

### Why it matters
Recent work significantly improved the default verification architecture.
This is now one of the most important core subsystems in AEL.

### Current status
Confirmed in the current repository:
- suite / task / worker organization
- parallel worker execution
- worker-safe logging
- per-resource locking
- worker-level repeated verification
- corrected fallback behavior for some board paths
- durable execution-model documentation in `docs/default_verification_execution_model.md`
- preferred `verify-default repeat --limit N` CLI for worker-level repetition

Still needing consolidation or expansion:
- stronger automated coverage for more contention and partial-failure cases
- clearer evidence around some intermittent bench failures
- more explicit documentation of lock coverage and limits

### Immediate goals
- expand tests for resource contention, partial failure, and concurrency edge cases
- validate logging and archive correctness under more adverse concurrency scenarios
- define expected behavior under partial failure more explicitly
- identify any missing tests that still require live bench confirmation

### Key questions
- Is the current worker model complete enough for future scale-out?
- Are resource locks covering all real shared-resource cases?
- Is repeated verification behavior fully aligned with intended per-board progression?
- Are current tests sufficient, or do we still rely too heavily on live bench behavior?

### Suggested outputs
- extend tests for worker, repeat, locking, and failure behavior
- add focused skill/workflow notes for repeat mode, probe fallback, and worker resource locking

Current repo state:
- targeted tests now cover distinct-resource overlap, shared-lock serialization, lock hold across worker repeat windows, and parallel partial-failure completion
- the main remaining gap is broader edge-case coverage rather than the absence of any concurrency-focused tests

---

## 2. Workflow / Skills Documentation

### Why it matters
AEL is now producing reusable engineering knowledge faster than it can be remembered informally.
This knowledge should be captured before it is lost or repeatedly rediscovered.

### Current approach
For now, skills/workflow knowledge should be stored as lightweight Markdown documents under:
- `docs/skills/`

This is intentionally simple.
The goal is to capture useful engineering knowledge first and formalize it later.

### Immediate goals
- continue using `docs/skills/README.md` as the default style guide
- keep skill documents grounded in real, high-value cases already encountered
- expand the initial set of reusable workflow notes
- use these documents to support future AI/Codex/human work

### First suggested skill documents
- `docs/skills/esp32c6_intermittent_bench_failure.md`
- `docs/skills/default_verification_repeat_mode.md`
- `docs/skills/probe_fallback_policy.md`
- `docs/skills/worker_resource_locking.md`

Current repo state:
- `docs/skills/README.md` exists
- `docs/skills/esp32c6_intermittent_bench_failure.md` exists
- `docs/skills/default_verification_repeat_mode.md` exists
- `docs/skills/probe_fallback_policy.md` exists
- `docs/skills/worker_resource_locking.md` exists

### Key questions
- What knowledge is reused often enough to deserve a skill document?
- How should confirmed conclusions be separated from hypotheses?
- How should these documents evolve later into more formal workflow or machine-readable formats?

---

## 3. Observability / Evidence / Diagnostics

### Why it matters
AEL should increasingly be able not only to report pass/fail, but also to explain failures in a structured and useful way.

This is especially important for intermittent bench-side issues.

### Current motivation
Recent ESP32-C6 behavior showed that current diagnostics are still too coarse in some cases.
For example, failures may currently appear only as:
- unreachable
- verify failed

These labels are useful but not sufficient.

Current repo state:
- first-pass structured meter reachability diagnostics now exist
- early meter failures can emit structured observations into results/evidence
- verify-stage evidence is richer than before, but still not yet a full failure taxonomy

### Immediate goals
- improve failure classification further
- capture richer evidence for intermittent failures
- distinguish bench connectivity issues from DUT/runtime issues more clearly
- define structured output for failure analysis

### Areas to improve
- network / route / service reachability visibility
- verify-stage failure breakdown
- timing / repeated-run correlation
- environment snapshotting where useful
- structured failure summary

### Key questions
- What minimum evidence should always be captured on failure?
- Which diagnostics are worth automating now?
- How should failure evidence be stored and surfaced?

### Immediate focus
ESP32-C6 intermittent failure diagnosis should be treated as the first high-value example.

Current caution:
- current remaining ESP32-C6 instability appears more likely bench-side, especially on the host Wi-Fi / network path to the meter
- observability and classification may still be worth refining, but this issue should not currently be treated as evidence of an AEL core execution-model defect

---

## 4. Unified Instrument Model / Network Interface

### Why it matters
AEL will become simpler and more stable if instruments are exposed through a consistent model and interface.

Without this, core logic risks becoming fragmented by instrument-specific behavior.

### Goals
- define a unified instrument abstraction
- define common network-facing semantics
- separate instrument capabilities from instrument implementation details
- make AI interaction with instruments easier and more consistent

Current repo state:
- instrument manifests, registry lookup, instrument capability metadata, and instrument CLI flows already exist
- stage explanation and strategy resolution already surface some instrument communication and capability metadata
- the implementation is still only partially unified; probe-specific and instrument-specific paths still coexist
- durable architecture reference now exists in `docs/instrument_model.md`
- active runtime/report/archive surfaces now prefer `control_instrument*` and keep legacy `probe*` data under explicit `compatibility` objects where still needed

### Topics to address
- discovery
- connect / disconnect
- health / status
- capabilities
- command execution
- result collection
- error model
- timeout / retry semantics

### Key questions
- What is the minimum common instrument interface?
- Which capabilities should be standardized across instruments?
- How should board- or instrument-specific behavior be represented without polluting the core model?

### Desired outcome
A stable instrument model that reduces special-case logic in the AEL core.

---

## 5. Unified DUT Model / Interface

### Why it matters
As AEL supports more boards, the DUT model needs to become more explicit and more uniform.

AEL should not become just a collection of board-specific scripts and policies.

### Goals
- define a common DUT abstraction
- standardize core DUT lifecycle actions
- separate common behavior from board-specific policy
- make DUT state and expected transitions more explicit

Current repo state:
- DUT assets and CLI workflows already exist in partial form (`dut create`, `dut promote`, golden vs user assets)
- board configs are still the dominant operational representation for live execution
- a single unified DUT runtime model is not yet clearly established across the codebase
- durable architecture reference now exists in `docs/dut_model.md`
- canonical runtime/archive/report objects now include `selected_dut`, `selected_board_profile`, and `selected_bench_resources`

### Topics to address
Examples of common DUT actions may include:
- power on / off
- reset
- boot mode selection
- flash / program
- run
- verify
- observe state
- recover from failure

### Key questions
- What actions belong in the common DUT interface?
- What state should the DUT model expose?
- How should board-specific behavior and constraints be represented?

### Desired outcome
A cleaner core architecture with less board-specific branching.

---

## 6. Connection / Resource / Bench Model

### Why it matters
AEL operates on real hardware benches, not just software jobs.
The system must model real dependencies accurately.

This affects:
- parallel execution
- locking
- diagnostics
- scheduling
- stage explanation
- configuration clarity

### Goals
- represent real bench dependencies explicitly
- distinguish exclusive vs shared resources
- define resource ownership and usage clearly
- avoid false implicit assumptions inherited from legacy behavior

Current repo state:
- connection normalization, bench setup resolution, inventory connection description, and worker resource locks already exist
- the repo already models several important dependency classes explicitly
- the main remaining need is consolidation, clarification, and better coverage of edge cases rather than starting from zero
- durable architecture reference now exists in `docs/bench_resource_model.md`

### Topics to address
- DUT-to-instrument connections
- probe bindings
- instrument endpoints
- serial ports
- meter-backed paths
- explicit vs implicit bindings
- fallback policy
- resource sharing rules

### Key questions
- Which resources are physical, logical, exclusive, shared, or virtual?
- Which bindings must be explicit?
- Which fallback behaviors should remain, and which should be removed?

### Desired outcome
AEL should reflect the real bench model instead of relying on hidden assumptions.

---

## 7. Board Bring-Up and Reusable Verification Patterns

### Why it matters
AEL is expected to expand to more boards.
Board onboarding must become more systematic and more reusable.

### Goals
- define a cleaner bring-up path for new boards
- define reusable verification patterns
- reduce one-off setup work
- make future expansion faster and more reliable

### Topics to address
- minimal board onboarding flow
- golden target / golden test patterns
- board policy placement
- reusable GPIO / UART / communication verification patterns
- board-specific exceptions

### Key questions
- What is the minimum path from new board definition to meaningful verification?
- Which test patterns should become standard?
- Which board differences should remain explicit rather than abstracted away?

---

## 8. Diagnostics and Reporting Structure

### Why it matters
As AEL grows, reporting must become easier to interpret and more useful for both AI and humans.

### Goals
- produce more structured reports
- separate raw evidence from interpretation
- improve visibility into why a run passed or failed
- make repeated-run and intermittent-run behavior easier to analyze

### Topics to address
- standardized failure summary format
- stage-level result reporting
- resource usage visibility
- repeat-run summaries
- intermittent failure reports
- architecture vs bench-side interpretation

---

## 9. Stress / Regression Validation

### Why it matters
Recent live runs were useful, but future confidence should not depend only on ad hoc observation.

### Goals
- define stronger validation for concurrency behavior
- define repeat and stress scenarios intentionally
- identify core behaviors that require automated test coverage
- avoid regressions in worker / locking / repeat semantics

Current repo state:
- unit tests already cover important pieces of default verification, probe binding, stage explanation, connection modeling, and instrument Wi-Fi flows
- recent live validation also exercised parallel suite behavior and worker-level repeat behavior
- additional targeted tests now cover key worker contention and partial-failure execution-model cases
- unstable-bench behavior still needs some live validation and possibly more simulated edge-case coverage

### Topics to address
- repeated suite-level vs worker-level semantics
- partial failure handling
- resource contention cases
- archive/log correctness under concurrency
- expected outcomes under unstable bench paths

### Key questions
- Which concurrency and repeat behaviors should be covered by automated tests?
- Which behaviors still need live bench validation?
- What should count as sufficient confidence before expanding the architecture further?

---

## Recommended Near-Term Sequence

### Recommended next steps
1. Continue the next observability pass for ESP32-C6 failure modes, especially finer verify-stage breakdown
2. Extend automated coverage further for additional contention and failure edge cases where useful
3. Continue consolidating the instrument model around current manifest/registry/capability mechanisms
4. Continue consolidating the DUT model around current asset and board-profile mechanisms
5. Continue clarifying the bench/resource/connection model and its operational consequences

---

## Working Principle

The current priority is not to add many new features quickly.

The current priority is to strengthen the foundations:
- execution model
- resource model
- observability
- reusable engineering knowledge
- clean abstraction boundaries for instruments and DUTs

AEL will move faster later if these layers are made clear now.

---

## Notes

This worklist should be updated as the architecture becomes clearer and as Codex review against the repository produces new findings.

Some items here are already partially implemented.
The goal of this document is not to imply they are absent, but to clarify which areas still deserve focused consolidation, design clarification, testing, or extension.

When updating this worklist, separate:
- confirmed repo state
- reasonable interpretation
- open questions still requiring live bench confirmation
