# Cloud Instrument Registration and Session Model v0.1

## Purpose

This document defines a bounded first model for cloud-instrument registration and session handling in AEL.

It is intentionally narrow.
It does not define a full cloud service or a full security architecture.

Its purpose is to describe the minimum concepts AEL should preserve so current local bridge and network-native instrument work can evolve into a cloud-connected model later.

It is explicitly a higher-layer document.
It is not the current primary implementation target.

## Scope

This document covers:

- cloud-facing instrument registration concepts
- session concepts between orchestration and instrument nodes
- control-plane expectations
- how this fits current AEL architecture

This document does not define:

- full auth protocol
- tenant model
- fleet management
- production relay infrastructure
- complete retry or queueing semantics

It also does not redefine the lower local instrument-facing API.
That lower layer should exist independently and should be reused by the higher cloud-facing layer.

## Layering Position

The agreed model is:

1. lower layer: Local Instrument Interface / Instrument Native API
2. higher layer: cloud-facing registration / session / remote orchestration

This document is about Layer 2.

Layer 2 should be built on top of Layer 1.
It should not bypass it or replace it with a separate incompatible command model.

## Current Architectural Position

At the current repo stage:

- AEL already supports network-facing instruments
- AEL already supports bridge daemons that expose local hardware as network-facing instruments
- AEL does not yet implement cloud registration or session routing

So this document is a compatibility-preserving forward model, not a claim of current implementation.

The current implementation phase should still focus on hardening Layer 1.

## Dependency on the Lower Layer

The higher cloud-facing layer assumes the lower local layer already provides:

- stable instrument identity
- capability description
- health/doctor semantics
- direct command/result operations

If the lower layer is unstable, the higher layer should not be implemented broadly yet.

## Core Model

The minimum future cloud path should support three logical roles:

1. `orchestrator`
- plans work
- selects instruments by capability and status
- opens or assigns sessions

2. `instrument_node`
- represents a local instrument or bridge daemon
- owns the physical access to hardware
- executes instrument-facing commands

3. `session`
- a bounded control relationship between orchestrator and instrument node for one active work context

## Registration Model

### Registration Goal

Registration lets orchestration know:

- which instrument node exists
- what identity it has
- what capabilities it exposes
- what health/state it is currently in
- how it can be reached

### Recommended First Registration Shape

A first bounded registration payload should include:

- stable node identity
- instrument id or bridge-managed id
- capability summary
- communication surfaces
- current health/status
- software/profile version

Example conceptual fields:

- `node_id`
- `instrument_id`
- `identity_kind`
- `identity_value`
- `capabilities`
- `surfaces`
- `health`
- `profile_version`

### Preferred Connectivity Direction

Future cloud registration should allow an instrument node to initiate the connection outward.

Reason:

- many devices will be behind NAT
- local-user networks should not require inbound exposure

So the preferred future pattern is:

1. instrument/bridge starts
2. authenticates outward
3. registers itself
4. opens a persistent control channel

This is more realistic than requiring cloud to dial into every user network.

## Session Model

### Session Goal

A session is a bounded orchestration-to-instrument interaction context.

It is useful for:

- exclusive use of a physical instrument for a task
- open/close semantics where a transport or device handle matters
- stateful data streams such as UART or capture

### Minimum Session Concepts

A first bounded session model should support:

- session creation
- session ownership
- session health
- session close/release

Conceptual fields:

- `session_id`
- `node_id`
- `owner`
- `state`
- `opened_at`
- `last_activity_at`

### Session States

Useful bounded state set:

- `pending`
- `active`
- `closing`
- `closed`
- `failed`

This is enough for a first model without overdesigning job orchestration.

## Control Plane vs Data Plane

The registration/session model belongs to the control plane.

Control-plane examples:

- register
- advertise capabilities
- report health
- acquire session
- release session
- submit command metadata

Data-plane examples:

- UART bytes
- waveform blocks
- meter sample streams
- large log payloads

The first implementation may still tunnel some data-plane traffic through simple HTTP endpoints.
But the architecture should keep the distinction explicit.

## Health Model

Registration and session handling should work with the same high-level health categories already emerging in current AEL:

- reachable / unreachable
- transport available / unavailable
- API available / unavailable
- instrument function degraded

This is important because cloud orchestration should not confuse:

- orchestration defects
- bench/network defects
- device-specific degraded conditions

## Ownership and Locking Relationship

The future cloud session model should align with the existing AEL resource-locking model.

Practical implication:

- session ownership should map cleanly onto instrument/resource ownership
- the same physical node should not be assigned incompatible simultaneous sessions unless explicitly designed for that

This preserves continuity with:

- `selected_bench_resources`
- resource keys
- worker locking behavior

## First Implementation Boundary

The first implementation should stay bounded.

A realistic first step later would be:

1. one local bridge daemon or one network-native instrument
2. one simple outward or local registration endpoint
3. one active session at a time
4. simple status + doctor + open/close path

That is enough to prove the model without building a full cloud platform.

## Relation to Current USB-UART Bridge Work

The USB-UART bridge daemon is already close to a useful cloud-ready node shape because it has:

- stable identity handling
- discovery and doctor paths
- network-facing API
- open/close/read/write operations

What it lacks is:

- registration
- orchestrator-issued session identity
- ownership model
- remote routing/auth

So it is a good future candidate for the first real implementation of this document.

But the current primary value of the USB-UART bridge daemon is still at Layer 1:

- it is a concrete Local Instrument Interface / Instrument Native API implementation
- it proves stable identity, doctor, and network-facing access
- it does not yet need cloud registration/session features to be useful

## Current Status

Confirmed current repo state:

- no cloud registration/session implementation exists yet
- current repo does have the architectural building blocks needed to add one later without a broad rewrite

Reasonable interpretation:

- this model should remain light and additive
- it should reuse current instrument identity, capability, doctor, and bridge patterns

## Related Documents

- [cloud_instrument_architecture_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/architecture/cloud_instrument_architecture_v0_1.md)
- [cloud_instrument_profile_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/cloud_instrument_profile_v0_1.md)
- [usb_uart_bridge_daemon_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/instruments/usb_uart_bridge_daemon_v0_1.md)
