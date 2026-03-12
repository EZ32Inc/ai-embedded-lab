# Cloud Instrument Architecture v0.1

## Purpose

This document explains why cloud-capable instruments matter in AEL and how they fit the current repository architecture.

It is a durable architecture note, not a session log.

## Core Position

An AEL instrument should be treated as a network-capable execution node whenever practical.

This does not mean every instrument must be cloud-hosted today.
It means the preferred architectural direction is:

- AEL talks to instruments through explicit communication surfaces
- those surfaces should be network-native or easily bridged into a network form
- local and cloud orchestration should reuse the same instrument-facing contract as much as possible

## Two-Layer Model

The agreed model is explicitly two-layered.

### Layer 1: Local Instrument Interface / Instrument Native API

This is the lower layer and the current implementation target.

It is the orchestration-facing interface that directly talks to one local or LAN-reachable instrument node.
It should be derived by refactoring and normalizing the existing instrument network interface already used in current AEL work.

This layer is responsible for:

- direct command/result interaction with an instrument
- local doctor/status behavior
- capability-facing operations
- local bridge-daemon access
- network-facing access to a bench-local instrument

In current AEL terms, this is the immediate practical target.
It is the layer current implementation work should focus on.

### Layer 2: Cloud-Facing Registration / Session / Remote Orchestration

This is the higher layer and is future-facing.

It is built on top of the Local Instrument Interface / Instrument Native API layer.

This layer is responsible for:

- node registration
- remote session ownership
- cloud-side routing
- remote orchestration coordination
- future auth/ownership/audit concerns

This layer is not the primary implementation scope of the current phase.

## Current Implementation Focus

The current implementation phase is focused on Layer 1:

- refactoring the existing instrument network interface
- turning it into a clearer Local Instrument Interface / Instrument Native API
- preserving a clean path upward to future cloud-facing behavior

The current phase is not primarily about directly implementing cloud registration/session infrastructure.

Under this model, moving from:

- local AEL -> local instrument

to:

- cloud AEL -> remote instrument

should not require a different instrument architecture.

The key dependency is:

- Layer 2 should reuse Layer 1
- it should not replace or bypass it

## Why This Matters

### Local architecture naturally becomes cloud architecture

If an instrument already exposes a normalized network-facing interface, then cloud use is not a separate product mode.
It is mainly a deployment change.

The main architectural delta becomes:

- authentication
- routing
- registration
- ownership
- logging and audit

The core command path does not need to be reinvented.

### Instruments become nodes, not accessories

In a cloud-ready AEL model, an instrument is not just a PC-attached helper device.
It behaves more like a bench node with:

- identity
- capabilities
- status
- communication endpoints
- command handling
- result and evidence return

This is a better fit for AI-driven orchestration than a purely local driver model.

### "Cloud brain + local hardware body" becomes realistic

AEL is already aimed at AI-assisted embedded-lab execution.
Network-native instruments make a natural split possible:

- cloud or remote orchestration as the planning/control layer
- local instruments as hardware-facing execution nodes
- DUTs as the manipulated and verified objects

That is a stronger architectural direction than a traditional desktop-only embedded toolchain.

## Position in Current AEL

This is not a new top-level architecture part.

Cloud-capable instruments fit inside the current AEL architecture mainly through:

- Hardware Model and Resource Contract
- Adapters and Capability Surfaces
- Evidence, Diagnostics, Reporting, and Archive

and operationally through:

- Run Resolution and Planning
- Operational Knowledge / Workflow Layer

Reasonable interpretation for the current repo:

- AEL is not yet a cloud-orchestration product
- but the current instrument direction already supports network-facing devices
- the USB-UART bridge daemon is an early concrete example of this direction

## Architectural Principles

### 1. Prefer network-native instrument interfaces

When practical, the preferred instrument interface should already be reachable over a normalized network contract.

Examples:

- HTTP JSON
- WebSocket
- TCP command endpoint
- a local bridge daemon that converts local USB/serial access into a network-facing instrument

### 2. Keep local mode and cloud mode protocol-compatible

The same instrument-facing schema should be reusable across:

- local direct/LAN mode
- local bridge mode
- remote relay or cloud mode

Transport profile may differ, but the command/result model should stay close.

### 3. Separate control plane from data plane

Control-plane concerns include:

- registration
- capability discovery
- selection
- session/task assignment
- health/status

Data-plane concerns include:

- UART streams
- waveform capture
- meter samples
- flash output
- large evidence payloads

This distinction should exist early, even if the first implementation keeps both over simple HTTP JSON.

### 4. Capabilities must be machine-readable

Cloud orchestration cannot depend on operator memory.
Instrument nodes need clear capability metadata, such as:

- supported surfaces
- measurement and control capabilities
- channel counts
- latency and throughput expectations
- local buffering or storage limits

### 5. Active outbound connectivity is a valid first-class model

For real cloud deployments, many instruments will sit behind NAT or user-managed networks.

So AEL should not assume cloud always connects inward.
An equally valid model is:

- instrument/bridge boots
- authenticates outward
- opens a persistent outbound channel
- cloud orchestration uses that established channel

This is especially relevant for future AEL bench nodes outside a lab LAN.

## Current Repo Signals

The current repository already contains useful signals toward this model:

- manifest-backed instrument identity and capability metadata
- normalized communication-surface thinking in instrument specs
- the USB-UART bridge daemon as a bridge from local USB hardware to a network-facing AEL instrument
- growing emphasis on stable instrument identity instead of volatile local paths

What is not yet present:

- cloud registration flow
- cloud relay/session routing
- auth and ownership architecture
- formal control-plane/data-plane split in runtime code

Reasonable interpretation:

- Layer 1 is already partially real in the repo
- Layer 2 is still architectural/spec groundwork, not a main implementation surface

## What This Document Does Not Claim

This document does not claim that AEL already has:

- cloud orchestration
- internet-facing security hardening
- remote fleet management
- multi-tenant device ownership

It only states that the current instrument direction should preserve a clean path toward those capabilities.

## Recommended Near-Term Direction

1. Continue treating network-facing instruments and local bridge daemons as first-class instruments.
2. Keep instrument identity stable and machine-readable.
3. Refactor the current instrument network interface toward a clearer Local Instrument Interface / Instrument Native API.
4. Prefer reusable command/result schemas across local and future remote profiles.
5. Avoid local-only assumptions that would block later cloud routing.
6. Keep security, registration, and relay concerns as explicit higher-layer future work rather than hidden assumptions.

## Related Documents

- [ael_architecture_overview_2026-03-11.md](/nvme1t/work/codex/ai-embedded-lab/docs/architecture/ael_architecture_overview_2026-03-11.md)
- [instrument_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/instrument_model.md)
- [ael_instrument_spec_v0_22.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/ael_instrument_spec_v0_22.md)
- [ael_instrument_communication_access_spec_draft_v0_2.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/ael_instrument_communication_access_spec_draft_v0_2.md)
- [usb_uart_bridge_daemon_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/instruments/usb_uart_bridge_daemon_v0_1.md)
