# ESP32-JTAG Implementation Plan v0.1

Date: 2026-03-18
Status: Active Draft

## Purpose

This document turns the four instrument-layer docs into a concrete implementation plan for the current AEL codebase.

It is intentionally repo-specific. It names the current modules, the expected write areas, and the recommended order of work.

Source docs:

- [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md)
- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)
- [esp32_jtag_backend_skeleton_v0_1.md](./esp32_jtag_backend_skeleton_v0_1.md)

## Current Repo Reality

The repo already has an Instrument Action Model runtime:

- action registry: `ael/instruments/action_registry.py`
- dispatcher: `ael/instruments/dispatcher.py`
- current result helpers: `ael/instruments/result.py`
- current backends:
  - `ael/instruments/backends/esp_remote_jtag.py`
  - `ael/instruments/backends/stlink.py`
  - `ael/instruments/backends/usb_uart_bridge.py`

Important constraint:

The current runtime returns the older result shape:

- success: `ok`, `summary`, `data`, `logs`
- failure: `ok`, `error_code`, `message`, `retryable`, `logs`

The new four-doc pack defines the desired reference shape:

- success: `status`, `action`, `data`, `logs`
- failure: `status`, `action`, `error.code`, `error.message`, `error.details`

So this plan must include both:

1. implementing the ESP32-JTAG reference backend
2. deciding how to bridge or migrate the current result helper layer

## Implementation Goal

Deliver a Phase 1 reference backend for ESP32-JTAG that:

- supports `flash`, `reset`, `gpio_measure`
- follows the documented backend separation
- returns stable, structured results
- can be called through the current AEL dispatcher path
- is strong enough to become the template for later ST-Link and USB-UART alignment

## Scope

### Phase 1 required

- backend package skeleton
- `flash`
- `reset`
- `gpio_measure`
- typed backend exceptions
- transport boundary
- structural tests
- initial AEL integration

### Phase 2 follow-up

- `debug_halt`
- `debug_read_memory`
- alignment of the global IAM result helpers
- ST-Link migration onto the same pattern

## Write Areas

Primary expected write areas:

- `ael/instruments/backends/`
- `ael/instruments/dispatcher.py`
- `ael/instruments/result.py`
- `ael/instruments/action_registry.py`
- `tests/`

Recommended new package:

```text
ael/instruments/backends/esp32_jtag/
  __init__.py
  backend.py
  transport.py
  errors.py
  capability.py
  actions/
    __init__.py
    flash.py
    reset.py
    gpio_measure.py
    debug_halt.py
    debug_read_memory.py
```

## Recommended Delivery Order

### Step 1: Lock the result-contract strategy

Before implementation starts, decide one of these two paths:

#### Option A: bridge first

Keep current dispatcher/result helpers stable for now, and let the ESP32-JTAG backend normalize internally, then adapt back into the current AEL shape at the edge.

Use if:

- you want low-risk incremental delivery
- you do not want to update all existing instrument tests yet

#### Option B: migrate result helpers now

Update `ael/instruments/result.py` and callers toward the new reference shape immediately.

Use if:

- you want the reference backend to define the new global contract now
- you are willing to update existing backend and dispatcher tests in the same batch

Recommendation:

Start with Option A unless you explicitly want a larger IAM migration right now.

### Step 2: Create the ESP32-JTAG backend skeleton

Add the new backend package and keep the responsibilities strict:

- `backend.py`: dispatch + exception normalization
- `transport.py`: request/response
- `errors.py`: typed exceptions + error code mapping
- `capability.py`: support surface
- `actions/*.py`: per-action handlers

Do not add ST-Link refactors in the same change.

### Step 3: Implement typed errors and capability declaration

Minimum errors:

- `Esp32JtagError`
- `InvalidRequest`
- `TransportUnavailable`
- `RequestTimeout`
- `DeviceBusy`
- `ProgrammingFailure`
- `MeasurementFailure`
- `ResetFailure`

Minimum capability declaration:

- supports `flash`
- supports `reset`
- supports `gpio_measure`
- explicit `False` for `debug_halt` and `debug_read_memory`

### Step 4: Implement the transport layer

Add a minimal transport API:

```python
request(command: str, payload: dict[str, Any]) -> dict[str, Any]
```

Requirements:

- timeout handling
- invalid response handling
- connection failure handling
- no IAM semantics embedded in transport

### Step 5: Implement `reset`

Implement first because it is the smallest action and forces the basic contract into place.

Done when:

- invalid reset kind fails structurally
- transport success maps into normalized success
- backend/device reset failure maps into structured failure

### Step 6: Implement `flash`

Requirements:

- validate required fields
- validate firmware path exists
- map device response to normalized success data
- map failures to `programming_failure` or other typed errors

### Step 7: Implement `gpio_measure`

Requirements:

- validate non-empty channel list
- keep request surface explicit
- return normalized values and summary
- return structured measurement failure

### Step 8: Add placeholder Phase 2 action modules

Add:

- `debug_halt.py`
- `debug_read_memory.py`

These can initially return explicit structured unsupported behavior or placeholders, but the files should exist so the reference backend shape is complete.

### Step 9: Wire the backend into the current dispatcher

Current driver map in `ael/instruments/dispatcher.py`:

- `stlink`
- `esp_remote_jtag`
- `usb_uart_bridge`

Add the new backend in one of these ways:

#### Preferred

Register a new driver name such as `esp32_jtag`.

This keeps the reference backend explicit and avoids silent mutation of the existing `esp_remote_jtag` path.

#### Alternative

Refactor `esp_remote_jtag` to become the reference backend in place.

Use only if you want a direct in-place migration and are prepared to rewrite the current module substantially.

Recommendation:

Use a new explicit driver name first, then migrate old callers later.

### Step 10: Update the action registry if needed

Current registry names already largely match IAM, but request field expectations differ from the new docs.

Examples:

- current `flash` requires `firmware`
- new reference doc examples use `firmware_path`
- current `gpio_measure` requires `channel`
- new reference doc examples use `channels`

You need one compatibility decision:

1. migrate the registry to new names now
2. support both field styles temporarily
3. keep old names and document the difference

Recommendation:

Support both field styles temporarily in the backend and registry, then converge later.

### Step 11: Add tests before live validation

Required structural tests:

- unsupported action returns structured failure
- missing required fields fail correctly
- transport timeout maps correctly
- transport unavailable maps correctly
- invalid `reset_kind` fails correctly
- invalid firmware path fails correctly
- success result shape keys are stable

Suggested test files:

- `tests/test_esp32_jtag_backend.py`
- `tests/test_esp32_jtag_transport.py`
- `tests/test_esp32_jtag_action_mapping.py`

### Step 12: Run live validation

Follow the validation doc:

1. one smoke path: `flash -> reset -> gpio_measure`
2. repeat at least 5 times
3. run explicit failure-path checks
4. verify integration through the AEL dispatcher path

## Task Breakdown

### Task Group A: contract and skeleton

- choose bridge vs migrate result-contract strategy
- add new backend package layout
- add error types
- add capability declaration

### Task Group B: transport and Phase 1 actions

- add transport client
- add `reset`
- add `flash`
- add `gpio_measure`

### Task Group C: runtime integration

- register new driver in dispatcher
- adapt backend result into current AEL result contract if using bridge mode
- add placeholders for Phase 2 debug actions

### Task Group D: tests

- structural unit tests
- compatibility tests for request field names
- dispatcher integration tests

### Task Group E: live validation

- smoke path
- repeat validation
- failure-path validation

## Concrete Milestones

### Milestone 1: skeleton complete

Done when:

- backend package exists
- files match the documented layout
- errors and capabilities are defined
- dispatcher can import the backend

### Milestone 2: Phase 1 actions complete

Done when:

- `flash`, `reset`, `gpio_measure` are implemented
- structural tests pass
- placeholder debug action files exist

### Milestone 3: AEL integration complete

Done when:

- dispatcher can route to the new driver
- one integration test proves end-to-end dispatch path

### Milestone 4: reference-ready Phase 1

Done when:

- smoke path passes on hardware
- repeated validation threshold is met
- failure-path contract is demonstrated
- code is clean enough to act as the template for ST-Link alignment

## Risks To Watch

### Risk 1: result-shape drift

If the new backend returns one shape while the existing IAM runtime expects another, the "reference implementation" will not actually become the reference.

### Risk 2: action-field drift

Current registry field names and new doc examples differ.
If not handled explicitly, the backend will look compliant in docs but awkward in runtime.

### Risk 3: hidden reuse of legacy logic

If too much logic is silently copied from `esp_remote_jtag.py`, the new backend may inherit old shape and boundary problems instead of fixing them.

### Risk 4: mixing migration with expansion

Do not align ST-Link or USB-UART in the same batch as the first Phase 1 ESP32-JTAG reference implementation.

## Recommended First Coding Batch

If implementing immediately, the first batch should be:

1. add `ael/instruments/backends/esp32_jtag/`
2. add `errors.py`
3. add `capability.py`
4. add `transport.py`
5. add `backend.py`
6. add `actions/reset.py`
7. add one unit test file for structural behavior
8. register the new driver in the dispatcher

That is the smallest useful batch that creates a visible reference-backend path without overcommitting to all action details at once.

