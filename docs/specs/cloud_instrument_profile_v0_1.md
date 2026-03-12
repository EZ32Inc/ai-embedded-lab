# Cloud Instrument Profile v0.1

## Purpose

This document defines a bounded first profile for cloud-capable or cloud-ready instruments in AEL.

It does not define a full cloud platform.
It defines the minimum architectural profile needed so current instrument work does not block future cloud use.

This document assumes the agreed two-layer model:

- lower layer: Local Instrument Interface / Instrument Native API
- higher layer: cloud-facing registration / session / remote orchestration

The current implementation phase is focused on the lower layer.

## Scope

This profile applies to instruments that:

- already expose a network-facing interface
- or are wrapped by a bridge daemon that exposes a network-facing interface

Examples:

- Wi-Fi meter instruments
- ESP32JTAG-style adapters with network surfaces
- USB-UART bridge daemons running on a Linux host

This profile is about orchestration-facing behavior.
It is not a low-level hardware-driver specification.

More specifically, this document is primarily a profile for the lower local layer.
It exists so that future cloud-facing behavior can be built on top of a stable local instrument-facing contract.

## Layering Model

### Lower layer: Local Instrument Interface / Instrument Native API

This is the current implementation target.

It should be derived from refactoring the existing network interface already used by current AEL instruments and bridge daemons.

This layer should expose:

- stable identity
- machine-readable capability metadata
- network-facing command/result surfaces
- local doctor/status behavior

### Higher layer: Cloud-facing registration/session/orchestration

This is future-facing and built on top of the lower layer.

It should not define a separate incompatible instrument API.

It should add:

- registration
- session ownership
- remote routing
- future auth/ownership concerns

## Core Profile

A cloud-ready AEL instrument should provide or support:

1. stable identity
2. machine-readable capability metadata
3. one or more network-facing communication surfaces
4. explicit health/status reporting
5. a command/result contract that remains usable in both local and future remote deployment profiles

## Deployment Profiles

The same logical instrument may appear in several deployment profiles.

### Profile A: Local direct or LAN instrument

Examples:

- meter at `192.168.4.1:9000`
- ESP32JTAG at `192.168.2.63:4242`

This is already common in AEL.

### Profile B: Local bridge instrument

Example:

- USB-UART bridge daemon on Ubuntu exposing a local USB serial device as a network-facing AEL instrument

This is already present in the repo.

### Profile C: Cloud-relayed instrument

Future form:

- a local bench node or daemon authenticates outward to a cloud service
- the cloud routes commands over that established channel

This profile is not implemented in current AEL, but current instrument design should not block it.

The current implementation priority remains Profiles A and B, because they define and harden the lower local layer.

## Identity Requirements

A cloud-ready instrument must have a stable identity that does not depend on volatile local runtime paths.

Preferred identity sources:

1. explicit instrument id
2. vendor/device serial
3. stable bridge-managed identity
4. stable topology or by-path identity where unavoidable

Not suitable as primary identity:

- `/dev/ttyUSB0`
- `/dev/ttyACM0`
- transient DHCP address by itself

Reason:

- cloud or remote orchestration needs a durable way to address and reason about instrument nodes

## Capability Requirements

Capabilities should be machine-readable and specific enough for routing and task selection.

Examples:

- `measure.digital`
- `measure.voltage`
- `stim.digital`
- `observe.uart`
- `swd`
- `reset_out`

Useful metadata may include:

- channel count
- supported voltage range
- sample-rate limits
- latency expectations
- whether a surface is primary or compatibility-only

## Communication Surfaces

The profile assumes one or more explicit surfaces.

Each surface should declare, directly or through existing AEL manifest/spec rules:

- transport
- endpoint
- protocol
- invocation style where useful

This document adds one important cloud-oriented recommendation:

- keep the surface contract stable across local and remote deployment profiles whenever practical

## Control Plane and Data Plane

This profile distinguishes two logical planes.

### Control plane

Includes:

- registration
- capability advertisement
- status/health
- selection
- session/task assignment
- command initiation

### Data plane

Includes:

- UART streams
- waveform samples
- meter data
- flash output
- larger evidence payloads

The first implementation may still transport both over simple HTTP JSON.
But the distinction should remain explicit in architecture and future protocol design.

## Recommended Minimal Operations

For a cloud-ready or cloud-bridge instrument, the useful minimum operations are:

- `status`
- `describe_capabilities`
- `doctor`
- device-specific `open` / `close` if session state matters
- device-specific `read` / `write` / `measure` / `capture` / `reset` operations

This aligns with current local bridge work such as the USB-UART bridge daemon.

## Health and Doctor Requirements

The instrument should be able to report:

- whether it is present
- whether its selected device or transport is reachable
- whether it is openable/usable
- any stable-identity mismatch
- key configuration or transport errors

This is especially important for remote or semi-remote operation where an operator cannot infer state from local shell access.

## Security and Ownership

Security is intentionally out of scope for this first profile, but cloud use makes it unavoidable later.

Future layers should cover:

- instrument identity proof
- authentication
- authorization
- ownership
- revocation
- audit logging
- transport security

Current guidance:

- do not hardcode local-only assumptions that make these future layers harder

## Current AEL Fit

This profile fits current AEL without requiring a broad rewrite because the repo already has:

- instrument manifests
- communication metadata
- capability metadata
- doctor/inventory/reporting surfaces
- at least one concrete bridge daemon
- one bounded Local Instrument Interface pilot on the USB-UART bridge

What is still missing for a fuller cloud story:

- instrument registration protocol
- relay/session protocol
- cloud-side orchestration service
- persistent outbound-channel model

This is expected because the current phase is focused on the lower local layer, not direct implementation of the higher cloud layer.

## Recommended Documents for This Topic

At the current repo stage, the needed durable doc set is:

1. architecture note:
   - why network-native instruments matter for AEL cloud direction
2. bounded lower-layer profile/spec:
   - what the Local Instrument Interface / Instrument Native API must expose
3. higher-layer model note:
   - registration / session / remote orchestration expectations
4. concrete implementation docs:
   - per-instrument bridge or node docs, such as the USB-UART bridge daemon

This document is the bounded profile/spec.

## Related Documents

- [cloud_instrument_architecture_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/architecture/cloud_instrument_architecture_v0_1.md)
- [cloud_instrument_registration_and_session_model_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/cloud_instrument_registration_and_session_model_v0_1.md)
- [ael_instrument_spec_v0_22.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/ael_instrument_spec_v0_22.md)
- [ael_instrument_communication_access_spec_draft_v0_2.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/ael_instrument_communication_access_spec_draft_v0_2.md)
- [usb_uart_bridge_daemon_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/instruments/usb_uart_bridge_daemon_v0_1.md)
