# Cloud Instrument Bounded Path v0.1

## Purpose

This roadmap note describes the bounded path from current AEL instrument architecture to future cloud-ready instrument nodes.

It is not a broad cloud-platform roadmap.
It is a scoped execution note meant to preserve the right architecture while avoiding premature expansion.

## Current State

Confirmed current repo state:

- AEL already supports network-facing instruments
- AEL already has instrument manifests, capability metadata, and doctor/inventory/reporting surfaces
- AEL now has a first USB-UART bridge daemon that turns local hardware into a network-facing AEL instrument
- AEL does not yet have cloud registration, remote session routing, or cloud-side orchestration services

Agreed layering:

- lower layer: Local Instrument Interface / Instrument Native API
- higher layer: cloud-facing registration / session / remote orchestration

Current implementation focus:

- the lower local layer
- specifically, refactoring current network-facing instrument interfaces into a cleaner native local instrument layer

## Why This Matters

The current instrument direction already makes a future cloud model plausible.

The key architectural advantage is:

- the same instrument-facing contract can support local, LAN, bridge, and future cloud-relayed modes

This means the near-term task is not to build “cloud AEL.”
It is to keep local instrument work compatible with that future.

## Bounded Phase Order

### Phase A: Architecture and Spec

Goals:

- document why network-native instruments matter
- define a bounded lower-layer instrument profile
- define a bounded higher-layer registration/session model

Deliverables:

- architecture note
- profile/spec note
- registration/session model note

Status:

- now present in the repo

### Phase B: Bridge and Node Readiness

Goals:

- continue making local bridge daemons behave like clean instrument nodes
- preserve stable identity
- preserve doctor/status/capability surfaces

This phase is still lower-layer work.
It is the current implementation target.

Good candidates:

- USB-UART bridge daemon
- future bridge daemons for local-only hardware

### Phase C: First Local Registration Prototype

Goals:

- add a minimal registration endpoint or local registrar
- let one bridge/node advertise itself with:
  - identity
  - capabilities
  - status

Constraint:

- still local or single-host first
- not a public cloud design yet

This is the earliest point where higher-layer implementation should begin.

### Phase D: First Session Prototype

Goals:

- add one bounded session concept
- support one active owner/session at a time
- map session ownership onto current resource-locking expectations

Constraint:

- avoid general job platform design
- keep it small and instrument-centric

### Phase E: Cloud Relay / Outbound Channel Design

Goals:

- define how a node behind NAT authenticates outward
- define how the orchestrator sends commands over that channel

Constraint:

- do this only after Phases A-D are stable enough

## Working Principles

1. Keep local and cloud-facing command contracts as close as possible.
2. Treat the Local Instrument Interface / Instrument Native API as the immediate implementation target.
3. Build the higher cloud-facing layer on top of that lower layer.
4. Prefer additive architecture over broad rewrites.
5. Preserve stable instrument identity.
6. Keep control plane and data plane conceptually separate.
7. Reuse current doctor/status/capability patterns.
8. Build one concrete node path before designing general fleet behavior.

## Immediate Next Step

The immediate next step should remain local and bounded:

- keep improving bridge-style instruments as clean Local Instrument Interface / Instrument Native API nodes
- refactor current instrument network interfaces toward that lower-layer model
- do not start cloud relay implementation until a minimal local registration/session prototype is justified

## Exit Criteria for This Bounded Path

This bounded path is in good shape when:

- cloud-ready instrument architecture is documented
- bounded profile/spec exists
- bounded registration/session model exists
- at least one bridge/node implementation clearly fits that model

At that point, the next work can shift from architecture/spec clarification to minimal prototype implementation.

## Related Documents

- [cloud_instrument_architecture_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/architecture/cloud_instrument_architecture_v0_1.md)
- [cloud_instrument_profile_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/cloud_instrument_profile_v0_1.md)
- [cloud_instrument_registration_and_session_model_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/cloud_instrument_registration_and_session_model_v0_1.md)
