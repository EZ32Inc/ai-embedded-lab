# AEL Instrument Communication Access Specification Draft v0.2

## One-sentence definition

**Instrument communication access is the metadata and small normalized access description AEL uses to reach one selected communication surface of an instrument.**

---

## 1. Purpose

The AEL instrument specification defines:

- what an instrument is
- what capabilities it provides
- how it participates in orchestration

This document defines a narrower and more practical topic:

**how Orchestration reaches one communication surface of an instrument.**

This draft exists to clarify instrument-internal communication access without turning it into a new top-level architecture part.

It is intended to support:

- communication metadata clarity
- endpoint normalization
- auth/options normalization
- better diagnostics
- clearer doctor / inventory / planning output
- clearer summary / archive output
- gradual reuse across current runtime paths where that reuse stays small

It is **not** intended to define:

- a generic RPC framework
- a universal transport abstraction layer
- a new adapter architecture
- connection pooling or session management
- orchestration routing policy

---

## 2. Position in the AEL architecture

This specification does **not** define the main AEL “Connection” part in the six-part system.

Instead, it defines an **instrument-internal layer**.

### Important distinction

#### AEL Connection (ConnA)
Connection in the main AEL architecture refers to the physical/logical relationship between DUT and Instrument, such as:

- wiring
- pin mapping
- signal paths
- voltage compatibility
- reset / boot / SWD / JTAG / UART / GPIO relationships

That remains a separate architecture part.

#### Instrument Communication Access (ConnB)
This draft refers to how Orchestration reaches and invokes an instrument’s communication surface at runtime.

Examples:
- ESP32JTAG GDB remote surface
- ESP32JTAG web API surface
- meter TCP surface
- serial-accessed instrument surface

Therefore:

**instrument communication access is part of Instrument, not a seventh top-level architecture part.**

---

## 3. Scope

This draft applies to communication surfaces that AEL can actively use at runtime.

Examples in current or near-current AEL reality:
- ESP32JTAG GDB remote surface
- ESP32JTAG web API surface
- ESP32 meter TCP surface
- serial-accessed instrument surface

In the current repo, the most important live cases are:

- meter TCP access
- ESP32JTAG GDB remote access
- ESP32JTAG web API access

The current repo also already uses communication metadata and capability-surface metadata in:

- inventory
- doctor
- stage explain
- run summaries
- workflow archive output

This draft does not yet attempt to model:
- streaming session lifecycle
- multiplexed channels
- retries/backoff policy
- locking / arbitration
- secret management architecture
- generic request execution framework

This is intentional. The current AEL codebase is ready for clearer metadata and normalized descriptions, but not for a broad communication-runtime redesign.

---

## 4. Core model

Instrument communication access is derived from:

- an instrument identity
- a selected communication surface
- declared communication metadata
- optional runtime overrides

The result may be a **small normalized access description** that tells AEL how to reach that selected surface.

This normalized description should be treated as a helper object for clarity and diagnostics, not as the start of a universal connection/session framework.

### 4.1 Core questions

The minimum communication-access model should answer:

1. which surface is being used?
2. how is it reached?
3. where is it reached?
4. what communication contract is expected?
5. what additional access metadata applies?

---

## 5. Minimum communication metadata

The minimum metadata should be small and practical.

Recommended core fields:

- `transport`
- `endpoint`
- `protocol`
- `invocation_style` (optional)

### 5.1 transport
The carrier or connection medium.

Suggested values:
- `wifi`
- `ethernet`
- `usb`
- `serial`
- `local_process`
- `custom`

Important:
`transport` describes the carrier layer only.

Values such as:
- `http`
- `https`
- `websocket`
- `gdb_remote`

should **not** be treated as transport values here.

---

### 5.2 endpoint
The address or locator used to reach the selected surface.

Examples:
- `192.168.4.1:9000`
- `192.168.2.63:4242`
- `https://192.168.2.63`
- `/dev/ttyUSB0`
- `COM5`
- `local:openocd_instance_1`

The endpoint may remain a simple string at the metadata level.

However, it must **not** be assumed that an instrument has only one endpoint in all cases, because some instruments expose multiple surfaces.

---

### 5.3 protocol
A stable communication-contract identifier.

Examples:
- `gdb_remote`
- `gpio_meter_v1`
- `esp32jtag_web_api_v1`
- `serial_command_v1`
- `http_json_v1`

Important:
`protocol` should not be assumed to be identical to the current Python adapter/backend name.

If needed, implementation-facing metadata may separately include:
- `backend`
- `runtime_adapter`

---

### 5.4 invocation_style
Optional descriptive metadata about the dominant interaction style.

Suggested values:
- `request_response`
- `stream`
- `command_ack`
- `long_running_task`

In this draft, `invocation_style` is metadata only.  
It does not define runtime routing policy.

It is also optional because current AEL runtime does not depend on it.

---

## 6. Communication surfaces

An instrument may expose either:

### 6.1 Simple form
A single communication surface with a single metadata set.

Example:
- transport
- endpoint
- protocol
- optional invocation_style

This is appropriate for simpler instruments.

---

### 6.2 Structured form
A communication block containing one or more named surfaces.

Example:
```yaml
communication:
  primary: gdb_remote
  surfaces:
    - name: gdb_remote
      transport: wifi
      endpoint: 192.168.2.63:4242
      protocol: gdb_remote
      invocation_style: request_response
    - name: web_api
      transport: wifi
      endpoint: https://192.168.2.63
      protocol: esp32jtag_web_api_v1
      invocation_style: request_response
      auth:
        type: basic
      options:
        tls_verify: false
```

### Important note about `primary`
`primary` is descriptive only.

It should **not** be interpreted as:
- orchestration routing policy
- capability selection policy
- automatic runtime dispatch policy

Its purpose is only to indicate the nominal main surface in metadata.

---

## 7. Optional access metadata

Some surfaces need additional surface-local metadata.

This should remain optional and lightweight.

Examples:
- `auth`
- `options`
- `availability`
- `health_state`
- `notes`
- `backend`
- `runtime_adapter`

### 7.1 auth
Examples:
```yaml
auth:
  type: basic
  username: admin
  password_ref: inline_or_external
```

Suggested auth types:
- `none`
- `basic`
- `token`

This draft does not define a full secret-management model.

### 7.2 options
Examples:
- `tls_verify`
- `timeout_s`
- `suppress_warnings`

These are surface-local optional extensions, not part of the required core communication model.

### 7.3 availability / health_state
Examples:
- `available`
- `busy`
- `offline`
- `unknown`

These are useful for doctor/inventory/status surfaces, but are not required core fields.

---

## 8. Normalized access description

At runtime, AEL may normalize communication metadata for one selected surface into a more explicit access description.

This normalized form is useful for:
- doctor output
- inventory output
- explain-stage output
- diagnostics
- run summary / archive output
- future gradual reuse across runtime paths

### 8.1 Suggested normalized fields

Required or highly recommended:
- `owner_kind`
- `owner_id`
- `surface`
- `transport`
- `protocol`
- `endpoint`

Optional normalized fields:
- `host`
- `port`
- `scheme`
- `path`
- `auth`
- `options`
- `availability`
- `health_state`
- `resolution_source`

### 8.2 Notes on normalized fields

- `owner_kind` / `owner_id` are traceability fields
- `resolution_source` should describe where the final access facts came from:
  - runtime_override
  - instance_metadata
  - type_metadata
  - derived_default

This normalized description is a helper for runtime clarity.
It is **not** a new universal connection/session abstraction.

Current AEL already has partial normalized facts in several places, for example resolved endpoint, probe instance, selected endpoint, and communication metadata carried through summaries and archive output. This draft should align those patterns, not replace them with a heavy new model.

---

## 9. Diagnostics

One reason to define instrument communication access at all is to make failures easier to understand.

A normalized diagnostic shape is therefore useful.

Suggested fields:
- `ok`
- `surface`
- `endpoint`
- `protocol`
- `failure_kind`
- `error`

Suggested `failure_kind` values:
- `missing_endpoint`
- `parse_error`
- `dns_failure`
- `route_unreachable`
- `tcp_connect_failed`
- `tls_failure`
- `auth_failed`
- `protocol_unhealthy`
- `busy_or_locked`
- `unknown`

This draft does not define retry policy or recovery policy.

---

## 10. Minimal runtime helper direction

If AEL adds runtime helpers in this area, they should remain small and metadata-oriented.

Suggested first helpers:
- `validate_instrument_access_metadata(...)`
- `describe_instrument_access(...)`
- `normalize_instrument_access(...)`

Possible later helper:
- `check_instrument_access(...)`

Not yet:
- `open_connection(...)`
- generic session framework
- transport-independent execution layer

The goal is to reduce duplicated parsing and improve diagnostics, not to redesign runtime architecture.

### 10.1 Current implementation status

Current AEL already implements the metadata-first half of this direction:

- communication metadata exists in live manifests/configs
- capability-to-surface metadata exists in live manifests/configs
- validation exists for metadata shape
- doctor, inventory, stage explain, summaries, and archive output already surface much of this metadata

What is not implemented, and should remain out of scope for this draft, includes:

- runtime routing by protocol
- runtime routing by invocation style
- a universal connection layer
- a generic session/client framework

---

## 11. Mapping to current AEL reality

Likely current mappings include:

### Meter surface
- transport: `wifi`
- endpoint: `192.168.4.1:9000`
- protocol: `gpio_meter_v1`
- invocation_style: `request_response`

### ESP32JTAG GDB remote surface
- transport: `wifi`
- endpoint: `192.168.2.63:4242`
- protocol: `gdb_remote`

### ESP32JTAG web API surface
- transport: `wifi`
- endpoint: `https://192.168.2.63`
- protocol: `esp32jtag_web_api_v1`
- auth/options as needed

These examples show why instrument communication access belongs inside the Instrument area, while ConnA remains the separate DUT↔Instrument relationship layer.

---

## 12. Implementation guidance

A practical first implementation path should be:

1. keep this metadata-first
2. keep simple form where sufficient and structured multi-surface form only where needed
3. normalize only current live surfaces when that improves clarity
4. expose normalized access facts in:
   - doctor
   - inventory
   - stage explain
   - summaries
   - archive output
4. standardize diagnostic shapes where practical

Only later:
5. gradually let selected runtime paths reuse the normalized access facts

The main discipline is to keep the communication-access layer useful for description, diagnostics, and metadata normalization before trying to make it a runtime execution framework.

This draft should not force a broad runtime rewrite.

---

## 13. Explicit non-goals for Draft v0.2

This draft does not define:
- main AEL Connection (ConnA)
- a seventh architecture part
- session reuse
- connection pooling
- locking/arbitration
- universal transport adapters
- full protocol schemas
- secret management system
- generic RPC execution framework

It also does not redefine Instrument itself. Instrument architecture is already mature enough for the current phase; this draft only refines the instrument-internal communication-access layer.

---

## 14. Summary

The purpose of this draft is to define a **small, instrument-internal communication access layer**.

It exists to:
- clarify how Orchestration reaches one selected surface of an instrument
- support metadata normalization
- improve diagnostics
- reduce duplicated endpoint/auth/options parsing

while avoiding:
- a new top-level architecture part
- a heavy abstraction layer
- premature runtime redesign

This draft is therefore best treated as a temporary baseline for the ConnB discussion, while the next major architecture/specification effort can focus on the real AEL Connection part: ConnA.

So in AEL terms:

- **ConnA** remains the main architecture-level Connection part
- **ConnB** is best treated as part of Instrument
- this document is therefore an instrument communication access draft, not a full connection spec
