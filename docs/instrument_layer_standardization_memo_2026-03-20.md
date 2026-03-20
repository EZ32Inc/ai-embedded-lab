# Instrument Layer Standardization Memo 2026-03-20

## Goal

The real goal after the current schema/default-verification convergence is not
just more validation.

It is to make the entire instrument layer, including the interface boundary,
standardized.

For AI, `ST-Link`, `ESP32JTAG`, and `ESP32 meter` should eventually present one
coherent contract:

- the same metadata vocabulary
- the same action-dispatch model
- the same result envelope
- the same capability description style
- the same health / doctor semantics
- the same architectural boundary between interface and backend

That is what will make future instruments easier to add and make AI control more
reliable.

## Why This Matters Now

The six-worker parallel `default verification` baseline is now stable enough
that the next bottleneck is architectural consistency.

Right now AEL can drive multiple instruments successfully, but the instrument
layer is still partly split by historical implementation path.

That is acceptable during bring-up.
It is not the right long-term shape for an `AI-reliable engineering system`.

## Current State

The current repo already contains useful pieces of the target shape, but they do
not yet form one consistent module boundary.

### What Already Looks Good

Common metadata vocabulary already exists in several places:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

A common success/error envelope also already exists in the native APIs:

- success: `status: ok`, `data: ...`
- error: `status: error`, `error: { code, message, retryable, ... }`

Useful implementation anchors already exist:

- [jtag_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/jtag_native_api.py)
- [meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)
- [control_instrument_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/control_instrument_native_api.py)
- [stlink backend](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/stlink_backend/backend.py)
- [native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)

### Where The Layer Is Still Split

The current split is not only by instrument family. It is also by layer shape.

1. `ESP32JTAG` metadata is owned by `jtag_native_api`, but important control
   actions still enter through `control_instrument_native_api`.
2. `ESP32 meter` already has both metadata and actions in one native-API-facing
   module, but its action names are mapped from backend names like
   `gpio_measure` and `voltage_read`.
3. `ST-Link` currently exists mainly as a backend/action wrapper, not as a full
   first-class native instrument interface with the same metadata/doctor shape.
4. `native_api_dispatch` is still hard-coded by instrument id and split between:
   - `identify/get_capabilities/get_status/doctor`
   - `control_*`
   - action-specific helpers
5. `usb_uart_bridge` is actually one of the cleanest native-interface examples,
   but it is not yet the common structural template used by all instruments.

## Current Interface Differences

### 1. Metadata Ownership Is Inconsistent

- `ESP32JTAG`: metadata in `jtag_native_api`
- `ESP32 meter`: metadata in `meter_native_api`
- `ST-Link`: no matching first-class native metadata module yet
- `USB-UART bridge`: metadata methods exist on the daemon side

The result is that the AI-visible metadata contract exists, but not all
instruments reach it through the same architectural path.

### 2. Action Naming Is Inconsistent

Examples:

- AI-friendly / interface-side names:
  - `measure_digital`
  - `measure_voltage`
  - `preflight_probe`
  - `program_firmware`
- backend-side names:
  - `gpio_measure`
  - `voltage_read`
  - `flash`
  - `debug_halt`

This is manageable, but the translation boundary is not yet standardized.

### 3. Control Instruments And External Instruments Are Split By Special Case

Today there is a conceptual split between:

- `control_instrument_native_api`
- family-native modules such as `jtag_native_api` and `meter_native_api`

That split was useful while proving the first control-instrument paths, but it
is now becoming a source of structural inconsistency.

### 4. Doctor / Status Semantics Are Not Yet Fully Aligned

All three families can expose health, but the structure is still family-shaped.

- JTAG focuses on `network`, `gdb_remote`, `web_api`, `capture_subsystem`
- meter focuses on `network`, `meter_service`, measurement/stimulation surfaces
- ST-Link health is currently expressed mostly through flash/bootstrap behavior,
  not yet through the same first-class native `doctor` surface

We want family-specific health domains, but we also need a common top-level
contract for how they are reported.

### 5. Module Boundary Is Not Yet Uniform

The clean long-term pattern should be:

- interface module: AI-facing contract and result normalization
- backend module: family-specific execution details
- dispatcher/registry: routing only

Today, some instruments already look like that, some partly do, and some are
still hybrid.

## Target Contract

The target is not that every instrument supports the same actions.
The target is that every instrument supports the same interface model.

### Common Metadata Contract

Every instrument family should expose:

- `identify(config)`
- `get_capabilities(config)`
- `get_status(config)`
- `doctor(config)`

All of them should return the same envelope:

- success:
  - `status`
  - `data`
- error:
  - `status`
  - `error.code`
  - `error.message`
  - `error.retryable`
  - optional `error.details`

### Common Action Contract

Actions should be dispatched through one common instrument action surface, with
family support determined by capability advertisement.

Representative action vocabulary should be normalized around interface names,
for example:

- `program_firmware`
- `reset`
- `debug_halt`
- `debug_read_memory`
- `measure_digital`
- `measure_voltage`
- `stim_digital`
- `uart_open`
- `uart_close`
- `uart_write`
- `uart_read`
- `preflight_probe`

Backend-native names can still exist internally, but they should not leak as
parallel AI-facing contracts.

### Common Capability Model

Each instrument should advertise capabilities in the same shape:

- capability family name
- supported actions
- transport/surface used
- ownership/module information if useful
- optional limits/channels/params

This allows AI to reason uniformly about what an instrument can do without
needing family-specific command knowledge.

### Common Health / Doctor Contract

Each instrument should report:

- `reachable` or equivalent top-level availability
- `health_domains`
- per-domain `ok/state/summary`
- family-specific details nested under those domains

The domains can differ by family, but the contract shape should not.

## Target Module Architecture

The desired module pattern is:

1. one native interface module per instrument family
2. one backend module per instrument family
3. one dispatch/registry layer that does routing, not family logic

A clean target shape would look like this conceptually:

- `ael/instruments/interfaces/stlink.py`
- `ael/instruments/interfaces/esp32jtag.py`
- `ael/instruments/interfaces/esp32_meter.py`
- `ael/instruments/interfaces/usb_uart_bridge.py`
- `ael/instruments/interfaces/registry.py`
- `ael/instruments/backends/...`

In that model:

- interface modules normalize metadata, capabilities, doctor, and actions
- backend modules execute family-specific operations
- registry resolves instrument family to interface provider
- AI-facing callers talk to one consistent dispatch surface

## Recommended Migration Strategy

This should be done incrementally, not as a big rewrite.

### Phase 1: Interface Audit And Contract Freeze

Deliverables:

- define the standard instrument interface contract explicitly
- record current gap matrix across `ST-Link`, `ESP32JTAG`, `ESP32 meter`, and
  `USB-UART bridge`
- freeze the target action vocabulary and metadata envelope

This memo is the start of that phase.

### Phase 2: Introduce A Uniform Provider Interface

Add one internal provider contract for instrument families.

Example shape:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `invoke_action`

or equivalent explicit per-action registration.

The important part is not the exact method names.
The important part is that all families conform to one provider contract.

### Phase 3: Migrate ST-Link To A First-Class Native Interface

This should be the first migration target because it is currently the clearest
structural outlier.

Goal:

- give ST-Link the same first-class metadata and doctor surface as the others
- stop treating it only as a backend/action wrapper
- normalize its health and capability output at the interface layer

### Phase 4: Collapse ESP32JTAG Split Ownership

`ESP32JTAG` currently has a split between `jtag_native_api` and
`control_instrument_native_api`.

Goal:

- move to one family-owned interface module
- keep backend execution where it belongs
- remove the special-case feeling around `control_*` dispatch for JTAG paths

### Phase 5: Align Meter And USB-UART To The Same Provider Shape

These are closer already, but they should still be migrated to the same common
provider/registry structure so the architecture is actually uniform.

### Phase 6: Replace Hard-Coded Dispatch With Registry Routing

`native_api_dispatch` should stop deciding behavior through scattered `if
instrument_id == ...` routing.

Instead, it should resolve the provider by instrument family / manifest type and
then route through the common provider interface.

## What We Should Not Do

- do not try to make all instruments support the same actions
- do not erase family-specific health domains
- do not rewrite all backends at once
- do not mix orchestration verdicts into the native interface layer
- do not keep adding one-off helper surfaces that bypass the standard contract

## Proposed Immediate Next Step

The first real implementation step should be architectural, not behavioral.

I recommend this exact next step:

1. define a common instrument provider contract in code
2. add a registry that resolves one provider per family
3. implement the first provider adapter for `ST-Link`
4. keep behavior unchanged while normalizing interface shape

Why start with `ST-Link`:

- it is currently the most obvious mismatch against the target architecture
- it recently received meaningful reliability work, so this is a good moment to
  move it into the standard model
- if `ST-Link` can be expressed cleanly through the same interface contract,
  the same pattern will be easier to apply to JTAG and meter

## Review Focus

The main question for review is not wording.
It is whether this target boundary is the right one:

- one standardized instrument interface contract
- family-specific backend implementations behind it
- registry-based routing instead of special-case dispatch

If that direction is accepted, the next coding batch should start by defining
that provider contract and migrating `ST-Link` into it.
