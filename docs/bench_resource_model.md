# AEL Bench and Resource Model

## 1. Purpose

This document explains how AEL should think about bench setup, connection metadata, and shared runtime resources.

Its goals are:
- define the bench model clearly
- connect connection metadata to execution behavior
- explain how runtime resource locking relates to real hardware sharing
- separate confirmed current behavior from future cleanup

## 2. Core Position

The preferred AEL model is:

- the bench is a set of real connected resources
- a test plan describes which parts of that bench a run needs
- execution locks should reflect those real shared resources
- unrelated bench resources should not block each other

This means the bench model is not only documentation.
It directly affects:
- task explanation
- capability binding
- concurrency safety
- correctness of pass/fail interpretation

## 3. Confirmed Current Repo State

Confirmed:
- AEL already has connection normalization in `ael/connection_model.py`
- board configs already carry `default_wiring`, `observe_map`, `verification_views`, and `bench_connections`
- test plans can carry `bench_setup` and legacy `connections`
- default verification already derives resource lock keys from real runtime context
- lock keys already include important resource classes such as DUT identity, probe binding/endpoint, serial port, and instrument endpoint

Also confirmed:
- some bench semantics still live partly in docs, partly in config, and partly in runtime heuristics
- resource locking is intentionally simple and in-memory for the current process model
- some explanation paths still speak in probe-oriented terms because of legacy model seams

## 4. Bench Model Layers

The bench should be understood in layers.

### A. Physical connection layer

Examples:
- DUT GPIO connected to instrument digital channel
- DUT 3V3 connected to instrument ADC input
- reset line connected or intentionally unconnected
- shared ground present or required

This layer is represented today through fields such as:
- `default_wiring`
- `bench_connections`
- `bench_setup`
- `observe_map`
- `verification_views`

### B. Capability layer

Examples:
- flash via SWD or serial
- observe signal edges
- measure voltage
- stimulate digital lines

This layer connects physical bench arrangement to runtime operations.

### C. Resource ownership layer

Examples:
- one physical DUT
- one serial port
- one instrument endpoint
- one debug adapter endpoint

This layer drives locking and concurrency behavior.

## 5. Connection Metadata Meaning

Connection metadata should answer:
- what is connected
- how AEL should interpret that connection
- what warnings or validation errors should be raised

Current confirmed behavior:
- connection normalization merges default wiring with CLI overrides
- validation checks can detect missing coarse wiring and some semantic mismatches
- `bench_setup` supports instrument-linked verification setups more explicitly than older `connections`

Operational meaning:
- connection metadata is not only user documentation
- it helps determine what a check is supposed to observe and whether the declared setup is coherent

## 6. Resource Model Meaning

The resource model is the runtime projection of the bench model.

Its job is to answer:
- which workers can run in parallel
- which workers must serialize
- which conflicts are real versus accidental

Confirmed resource classes already represented in the current execution model:
- DUT identity
- probe endpoint or probe binding
- explicit flash serial port
- instrument endpoint

Reasonable interpretation:
- these cover the most important current contention cases for default verification
- future expansion may add more fine-grained or explicit resource classes if the bench grows more complex

## 7. Guiding Rule

The core rule is:

- parallelize unrelated work
- serialize only on real shared resources

This rule should guide:
- default verification execution
- future suite/task scheduling
- explanation of observed worker blocking
- future connection-model cleanup

## 8. Relationship to Default Verification

Default verification is where the bench/resource model is most operational today.

Confirmed behavior:
- the suite can run workers in parallel
- workers hold claimed locks for their execution window
- unrelated workers can progress independently
- shared resources intentionally serialize workers

This means the bench model is already affecting real runtime behavior, not just static docs.

## 9. Recommended Canonical Model

The long-term bench/resource model should distinguish clearly between:

1. Declared connections
- wiring and setup metadata

2. Required capabilities
- what the test needs to do

3. Bound resources
- which concrete instruments, ports, and DUT instances satisfy that need

4. Lock keys
- the runtime serialization projection of those bound resources

This sequence is important:
- do not derive locks from vague historical defaults
- derive them from resolved, real runtime ownership

## 10. Migration Direction

### Phase 1: Keep documenting current behavior

- explain how `bench_setup`, `observe_map`, and lock keys relate
- prefer explicit bench metadata over inherited assumptions

### Phase 2: Improve visibility

- expose relevant lock keys or resource summaries more directly in runtime/debug output
- make it easier to see why a worker is waiting
- prefer a canonical `selected_bench_resources` object in structured outputs so selected endpoints, control instruments, and connection digests are grouped together
- expose `resource_keys` and a grouped `resource_summary` in worker-oriented result payloads so tools do not need to parse lock strings ad hoc

### Phase 3: Tighten model alignment

- ensure explanation, connection metadata, and runtime lock derivation all describe the same bench reality
- reduce legacy naming that can imply false sharing

### Phase 4: Expand as needed

- add new resource classes only when a real bench need appears
- avoid over-modeling theoretical resources that do not yet matter

## 11. Confirmed Constraints and Open Questions

### Confirmed

- the current locking model is process-local and intentionally simple
- current connection metadata already supports useful validation and explanation
- current runtime behavior has been bench-validated for parallel independence and real shared-resource serialization in default verification

### Reasonable interpretation

- the main next need is better visibility and continued alignment, not a wholesale redesign

### Open questions

- should runtime output surface claimed resource keys directly
- which future bench arrangements will require additional explicit resource classes
- how much more of the bench model should be standardized in schemas versus left as pragmatic metadata

## 12. Related Files

- [ael/connection_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/connection_model.py)
- [ael/resource_locks.py](/nvme1t/work/codex/ai-embedded-lab/ael/resource_locks.py)
- [ael/verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [docs/default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)
- [docs/skills/worker_resource_locking.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/worker_resource_locking.md)

## 13. Short Guidance

When explaining or extending AEL bench behavior:
- start from real physical/resource ownership
- prefer explicit bench metadata over hidden defaults
- derive worker serialization from real conflicts
- do not treat historical probe assumptions as proof of actual bench sharing
