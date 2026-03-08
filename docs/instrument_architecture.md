# Instrument Architecture In AEL

## Purpose

This document clarifies the instrument model that AEL is already using in practice.

It is not a refactor plan. It is a boundary document for current and near-term implementation work.

The goal is to make instrument responsibilities explicit before more board paths, meter workflows, and future skills accumulate additional coupling.

## Why Instruments Matter In AEL

In AEL, instruments are not just external tools attached to the bench.

They are the bench-side capability layer through which AEL can:

- observe DUT behavior
- measure DUT signals or rails
- stimulate DUT pins or interfaces
- connect to bench-side services
- control or reset hardware
- export evidence for verification and debugging

Without instruments, AEL can still build or flash in some paths, but it cannot reliably validate real hardware behavior at the bench boundary.

This makes instrument architecture a core system concern, not a peripheral convenience.

## Current Instrument Usage In AEL

The current real instrument-driven path is centered on the ESP32-S3 meter.

Today AEL already uses instrument-related logic for:

### Discovery / Connect

- AP scan for `ESP32_GPIO_METER_XXXX`
- AP selection by full SSID or suffix
- Wi-Fi connect using manifest-provided AP details
- endpoint resolution to `192.168.4.1:9000`

Relevant current paths:

- [instruments.md](/nvme1t/work/codex/ai-embedded-lab/docs/instruments.md)
- [provision.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/provision.py)
- [__main__.py](/nvme1t/work/codex/ai-embedded-lab/ael/__main__.py)

### Identity / Ping

- `meter-ping` verifies the selected meter responds
- identity-like facts already come back in the ping response:
  - SSID
  - IP
  - port
  - MAC
  - firmware version

### Digital Measurement

- meter-backed GPIO signature verification uses `measure.digital`
- digital results are emitted to `instrument_digital.json`
- pass/fail is evaluated in `check.instrument_signature`

### Analog Measurement

- analog rail checks use `measure.voltage`
- results are emitted to `instrument_voltage.json`
- analog measurements are folded into the same verification result

### Evidence Generation

- AEL already emits instrument-backed evidence items such as `instrument.signature`
- run summaries and result artifacts already reference instrument evidence paths

This is already a meaningful subsystem, not a placeholder.

## Why Leaving Instrument Implicit Is Risky

If the instrument boundary remains implicit, responsibility will continue to leak across unrelated layers.

Likely failure modes:

- board configs absorb instrument detail that is really bench-side
- test plans become tied to one concrete instrument instead of a capability need
- DUT asset manifests mix board identity with instrument assumptions
- pipeline code accumulates more instrument-specific branching
- adding a new board becomes harder because instrument assumptions are copied ad hoc
- future skills get built on unstable boundaries and inherit current coupling

Concrete examples already visible in AEL:

- the meter path mixes instrument identity, endpoint assumptions, and connection mapping across test plans and DUT manifests
- instrument Wi-Fi connection flow lives outside the main run pipeline, while verification uses a separate instrument backend path
- adapter dispatch is capability-aware in intent, but still concrete-backend-heavy in implementation

None of these are catastrophic yet. They are early warning signs of a boundary that needs clearer definition.

## Proposed Definition Of An Instrument

An instrument in AEL is:

> A bench-side controllable capability provider that AEL can use to observe, measure, stimulate, connect to, or control real hardware during validation and debugging.

Important implications:

- an instrument is defined by capabilities first, not only by device type
- an instrument may expose one or more transports
- an instrument may provide multiple capabilities through one physical device
- an instrument is not the same thing as wiring, board identity, or test intent

## First-Pass Capability Model

The capability model should stay practical and close to what AEL already does.

### 1. Discovery / Connect

Examples:

- Wi-Fi AP discovery
- USB/serial presence detection
- endpoint selection
- network association

Current examples:

- `wifi-scan`
- `wifi-connect`
- `meter-list`
- `meter-ready`

### 2. Identity / Ping

Examples:

- ping / liveness
- instrument identity query
- firmware version / MAC / endpoint confirmation

Current example:

- `meter-ping`

### 3. Digital Observe / Measure

Examples:

- logic state classification
- toggle detection
- transition counting
- frequency-oriented measurement

Current example:

- meter `measure.digital`

### 4. Analog Measure

Examples:

- rail voltage sampling
- averaged analog measurement

Current example:

- meter `measure.voltage`

### 5. UART Observe

Examples:

- boot log capture
- expected token detection
- crash or download-mode detection

In current AEL this is handled as a run-stage check, but it still belongs conceptually to bench observation capability.

### 6. Flash / Program

Examples:

- DUT programming over serial, SWD, JTAG, UF2, or other transports

This may be provided by a debug probe, a USB bootloader path, or in some future cases an instrument-like bench controller.

### 7. Debug / Attach

Examples:

- SWD / JTAG connection
- monitor target listing
- halt / load / continue

Current example:

- ESP32JTAG and BMDA-style flows

### 8. Power / Reset Control

Examples:

- reset lines
- power-cycle control
- boot-mode assist

Parts of this already exist through recovery/control helpers even if not yet modeled as a clean instrument capability family.

### 9. Signal Drive / Stimulus

Examples:

- digital output drive
- pulse generation
- loopback/selftest drive

Current example:

- meter `stim.digital`

### 10. Capture / Export

Examples:

- measurement export
- raw capture export
- evidence file generation

This capability is important because AEL is evidence-driven. Bench operations need artifact-friendly outputs, not only console responses.

## Separation Of Responsibilities

This is the most important boundary.

### What Belongs To Board

Board describes DUT-side identity and DUT-side constraints.

Board should own:

- board id and name
- MCU target family
- build target / firmware target path
- DUT-safe or reserved pins
- DUT-side observe map if it is intrinsic to the board
- boot/reset quirks that are genuinely board-specific

Board should not own:

- concrete instrument channels
- meter AP identity
- Wi-Fi credentials
- bench-specific wiring assumptions that may vary by setup

### What Belongs To Test

Test defines what behavior is being validated.

Test should own:

- behavior expectation
- pass/fail conditions
- expected UART tokens
- digital/analog expectations
- required capability class
- measurement duration or test-local tolerances

Test may reference a specific instrument profile when the current system requires it, but that should be treated as a practical selection detail, not the core meaning of the test.

Test should not own:

- DUT board identity details beyond selecting a target board
- instrument transport internals
- bench connection topology beyond the signal mapping needed for this validation

### What Belongs To Instrument

Instrument describes the bench-side capability provider.

Instrument should own:

- instrument id and identity hints
- transports
- endpoint defaults or discovery hints
- available channels
- capability list
- capability limits
- selftest metadata
- safety notes

Instrument should not own:

- DUT board pin names
- test pass/fail meaning
- board-specific GPIO safety assumptions

### What Belongs To Wiring / Bench Setup

Wiring or bench setup defines how a concrete DUT is mapped onto a concrete instrument on a specific bench.

Bench setup should own:

- DUT signal to instrument channel mapping
- ground assumptions
- which AP or physical instrument instance is selected today
- serial port / USB port selection for this bench session
- any temporary bench overrides

Bench setup is where the real-world mapping lives. It should not be buried inside board identity or instrument identity.

Current practical direction:

- meter-based DUT-to-instrument mapping should live under an explicit `bench_setup` block in the test/config layer rather than under a generic `connections` bucket

## Applying The Model To The Current Meter Path

Use the current ESP32-S3 meter path as the concrete example.

### What The Instrument Is

Current instrument:

- [manifest.json](/nvme1t/work/codex/ai-embedded-lab/assets_golden/instruments/esp32s3_dev_c_meter/manifest.json)

This instrument is a Wi-Fi reachable meter with a TCP control path and optional serial/log path.

### What Capabilities It Currently Provides

From the manifest and current code:

- discovery/connect through Wi-Fi AP metadata
- identity/ping through the TCP endpoint
- `measure.digital`
- `measure.voltage`
- `stim.digital`
- selftest metadata sufficient for a bench-side self-check

### What Metadata / Profile Information It Needs

Current profile data includes:

- instrument id
- transport definitions
- TCP endpoint hint
- Wi-Fi SSID prefix and password
- AP IP and TCP port
- channel lists
- capability list
- safety notes
- selftest defaults

This is a good example of instrument-owned metadata.

### What Belongs To Instrument Vs Test Vs Board Vs Bench Setup

Instrument:

- `esp32s3_dev_c_meter`
- `192.168.4.1:9000` as default AP-side endpoint
- Wi-Fi AP family `ESP32_GPIO_METER_`
- available digital and analog channels
- digital/analog/stimulus capability presence

Test:

- which DUT signals should toggle, hold high, or hold low
- voltage range expectation for `3V3`
- measurement duration
- expected UART readiness token

Board:

- DUT is ESP32-C3 or ESP32-C6 or ESP32-S3
- DUT-side pin identity like `GPIO4/5/6/7`
- safe output assumptions for that board

Bench setup:

- `GPIO4 -> instrument GPIO11`
- `GPIO5 -> instrument GPIO12`
- actual selected meter AP such as `ESP32_GPIO_METER_E7F1`
- current USB port such as `/dev/ttyACM0`

That split is the practical model AEL should move toward more explicitly.

## Immediate Non-Goals

This document is not trying to do the following right now:

- not a full instrument subsystem refactor
- not a final universal interface for every future instrument
- not a complete multi-instrument orchestration redesign
- not a skills redesign
- not immediate support for every bench tool category
- not immediate elimination of all current coupling

The goal is boundary clarity first.

## Recommended Next Small Steps

Only modest next steps follow naturally from this document.

### 1. Standardize Instrument Profile Description

Keep using the manifest as the primary instrument description, but make current run/test code rely on it more consistently for:

- endpoint defaults
- channel metadata
- capability presence

### 2. Move Bench Mapping Out Of Board Identity Over Time

Today some mapping assumptions are split across board config and test config.

The next cleanup should make it clearer which mappings are:

- intrinsic board facts
- bench-specific DUT-to-instrument wiring

This can be a small targeted cleanup, not a large redesign.

### 3. Reduce Concrete Meter Special-Casing In Adapter Dispatch

Current adapter dispatch still has a concrete `esp32s3_dev_c_meter` backend embedded in the registry path.

A modest next step is to make capability-to-backend registration cleaner without redesigning the whole adapter system.

## Relationship To Future Skills

Skills still matter.

They will remain useful for:

- board bring-up guidance
- bench setup workflows
- reusable debugging procedures
- operator-facing automation patterns

But skills should be built on stable abstractions.

If instrument boundaries remain unclear, skills will encode unstable details and become brittle.

That is why instrument architecture should be clarified first:

- instruments define the bench-side capability layer
- skills should then orchestrate or guide against that clearer layer

## Summary

The practical AEL model is:

- board defines DUT identity and DUT constraints
- test defines behavior expectations
- instrument defines bench-side capabilities, transports, limits, and identity
- bench setup defines the real mapping between DUT and instrument for a specific run

That is the boundary that should guide future implementation cleanup.
