# ESP32JTAG Instrument-Level Interface Model Memo

Date: 2026-03-19

## Purpose

This memo defines the intended instrument-level interface model for
`ESP32JTAG`.

This is a boundary and object-model memo only.

It does **not** propose immediate code changes.

## Core Position

`ESP32JTAG` should not be modeled as a single-purpose JTAG probe.

It should be modeled as a **multi-capability bench instrument** that happens to
include debug/flash capability as one of its capability families.

That means its interface model should describe:

- instrument identity
- metadata / status / doctor surfaces
- action surfaces across multiple capability families
- transport and endpoint model
- boundary against AEL-side backend/dispatcher code

## 1. Instrument Identity

The instrument identity should be:

- `device_type`: `multi_capability_instrument`
- `instrument_family`: `esp32jtag`
- `model`: concrete hardware/firmware identity such as `ESP32JTAG`
- `instrument_id`: the configured bench identity, for example `esp32jtag_stm32f411`

Recommended identity concept:

`ESP32JTAG` is a networked bench instrument that exposes multiple hardware-side
capabilities through one physical device and one logical instrument identity.

It is not:

- only a `jtag_probe`
- only a `logic_analyzer`
- only a `reset controller`

It is one instrument with multiple capability surfaces.

## 2. Minimum Standard Interface Surface

The minimum standard instrument-level surface should contain four groups.

### A. Metadata Surface

This should answer:

- who the instrument is
- what firmware/protocol version it is speaking
- which transports/endpoints it exposes
- which capability families it claims to support

Minimum fields:

- `device_id`
- `device_type`
- `instrument_family`
- `model`
- `protocol_version`
- `communication_endpoints`
- `capability_families`

### B. Status / Doctor Surface

This should answer:

- is the instrument reachable
- are key transports healthy
- is the debug path healthy
- is the capture/control path healthy
- what specific degraded condition exists if not healthy

Minimum operations:

- `get_status`
- `doctor`

Minimum status domains:

- network reachability
- GDB/debug service reachability
- capture/control API reachability
- optional target enumeration health

### C. Action Surface

This is the runtime capability surface used by AEL.

At minimum, `ESP32JTAG` should be treated as exposing these capability families:

- `flash/program`
- `debug/attach`
- `reset/control`
- `digital capture/measure`
- `digital stimulus/control` if supported on the concrete instrument

Representative actions:

- `flash`
- `reset`
- `debug_halt`
- `debug_read_memory`
- `gpio_measure`

Possible future actions, if the instrument supports them cleanly:

- `stim_digital`
- richer capture exports
- target enumeration / attach introspection

### D. Transport Surface

This should explicitly model that one instrument may expose multiple endpoint
styles.

For `ESP32JTAG`, the interface model should assume at least:

- `debug_remote`
- `control_api`

Typical examples:

- GDB remote endpoint
- Web/HTTP or other control/capture endpoint

The interface model should not assume one transport per instrument.

## 3. What Should Be Symmetric With Meter / ST-Link

There should be symmetry in the **shape of the model**, not forced sameness in
the capabilities.

These should be symmetric across `ESP32JTAG`, `ESP32-S3 meter`, and `ST-Link`:

- explicit instrument identity
- explicit metadata surface
- explicit `get_status`
- explicit `doctor`
- explicit capability declaration
- explicit action surface
- explicit transport/endpoints description

This symmetry matters because AEL should be able to reason about all
instruments through a common object model.

## 4. What Should Not Be Forced Symmetric

These do **not** need forced symmetry:

- exact action set
- exact transport count
- exact provisioning flow
- exact doctor checks
- exact implementation layering

Examples:

- `meter` naturally has `measure_digital`, `measure_voltage`, `stim_digital`
- `ST-Link` naturally centers on debug/program actions
- `ESP32JTAG` naturally spans debug plus capture/control

So the model should be symmetric at the interface-contract level, while still
allowing different capability families per instrument.

## 5. ESP32JTAG As A Multi-Capability Instrument

This is the most important modeling rule.

`ESP32JTAG` should be defined as:

> one bench instrument with multiple capability families sharing one instrument
> identity

Recommended capability-family view:

- `debug_remote`
  - attach
  - halt
  - memory read
  - flash/program via debug path
- `capture_control`
  - GPIO/digital observation
  - signal verification support
  - other bench-side control features exposed by the device firmware/API
- `reset_control`
  - target reset behavior

This avoids the wrong simplification:

- "ESP32JTAG is just a JTAG adapter"

That simplification is not accurate enough for AEL.

## 6. Is The Current Remote-Service / Capability Model Enough?

Current answer:

- **good enough for backend execution**
- **not yet good enough as a full instrument-level interface model**

Why it is good enough today:

- AEL can already execute the main action path through
  [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)
- AEL already has a generic control-instrument native surface in
  [ael/instruments/control_instrument_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/control_instrument_native_api.py)

Why it is not yet enough:

- the current native surface is still generic `control_instrument`
- it does not declare `ESP32JTAG` as its own named multi-capability instrument
- it does not present an object model that is clearly parallel to
  `meter_native_api`
- it under-describes instrument identity and multi-surface capability ownership

So the current model is sufficient for execution, but not yet fully sufficient
for architectural clarity.

## 7. Does AEL Need A Separate `jtag_native_api`?

Answer: **probably yes, eventually; not because execution is blocked, but
because the instrument model is under-defined without it.**

The main reasons for a dedicated `jtag_native_api` would be:

- to give `ESP32JTAG` a first-class instrument identity parallel to
  `meter_native_api`
- to express metadata/status/doctor in terms of the actual instrument family,
  not only a generic control probe abstraction
- to describe multiple capability surfaces under one instrument object

The main reason not to rush it:

- the backend/action path is already working
- forcing an implementation too early could mix architectural cleanup with
  behavior changes

So the recommended architectural position is:

- a dedicated `jtag_native_api` is justified
- but it should start as an interface-model clarification layer, not as a large
  execution refactor

## 8. Recommended Object Model

Minimum conceptual object:

```text
Instrument
  id
  family = esp32jtag
  type = multi_capability_instrument
  model
  protocol_version
  endpoints:
    - debug_remote
    - control_api
  capability_families:
    - debug_remote
    - reset_control
    - capture_control
  metadata_surface
  status_surface
  doctor_surface
  action_surface
```

This should be the level at which AEL talks about `ESP32JTAG` as an instrument.

Below that level:

- backend packages
- transport adapters
- protocol details

can remain implementation details.

## 9. Boundary Decision

Recommended boundary:

- `esp32_jtag` backend remains the action-execution boundary
- a future `jtag_native_api` would be the instrument-level metadata/status/doctor
  boundary
- transport/protocol specifics remain below both

This keeps the model clean:

- instrument-level interface on one side
- action backend on the other side

without forcing them to be the same module.

## 10. Final Conclusion

The current repo already has a good `ESP32JTAG` backend package.

What it does **not** yet have is a fully explicit `ESP32JTAG` instrument-level
interface model parallel to `meter_native_api`.

So the architectural gap is real, but the gap is:

- not "missing backend package"
- not "missing execution capability"

The real gap is:

- missing first-class instrument identity and interface definition for
  `ESP32JTAG` as a multi-capability instrument

That is the correct problem statement for the next design step.
