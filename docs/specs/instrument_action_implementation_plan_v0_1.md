# Instrument Action Implementation Plan v0.1

## Status

Draft

## Related Documents

- [instrument_action_model_v0_1.md](instrument_action_model_v0_1.md) — model spec
- [instrument_action_examples_v0_1.md](instrument_action_examples_v0_1.md) — concrete workflow examples

---

## Purpose

This document defines the recommended implementation plan for the Instrument Action Model v0.1.

The goal is to move from the abstract model into a practical, incremental implementation that:

- is easy for AI agents to use
- supports current real AEL workflows
- avoids over-engineering
- gives a clean migration path for existing instruments
- uses ESP JTAG as the first strong multi-action example

This is an implementation plan, not a final architecture freeze.
The implementation should stay lightweight and be adjusted based on real usage.

---

## 1. Implementation Strategy

The recommended v0.1 strategy is:

1. define a small standard action registry
2. define a simple config format for DUTs and instruments
3. implement one central action dispatcher
4. implement a common result shape
5. integrate one multi-action instrument first
6. integrate narrow/specialized instruments next
7. validate the model on real workflows before expanding scope

The key idea is:

> Keep the AI-facing surface simple, even if the internal code is somewhat uneven at first.

---

## 2. Design Constraints

Implementation should follow these constraints.

### 2.1 AI-first interface

The top-level interface should be easy for AI to reason about.
Prefer:

- obvious names
- simple request dictionaries
- explicit structured results
- small number of top-level concepts

### 2.2 Action-first dispatch

The primary runtime idea is:

- an action is requested
- the system finds a compatible instrument
- the action runs
- a structured result is returned

### 2.3 Internal flexibility

Different instrument backends do not need to share deep internal code.
It is acceptable for:

- ST-Link backend
- USB-UART backend
- ESP JTAG backend

to have different implementation details, as long as they expose a common action surface.

### 2.4 Incremental delivery

The implementation should create value early.
Do not wait for the whole system to be perfect before integrating the first real instrument.

---

## 3. Recommended Deliverables

v0.1 implementation should produce the following deliverables:

1. action registry
2. config schema / representation
3. dispatcher
4. result formatter
5. ESP JTAG integration
6. one narrow/specialized integration
7. at least two real end-to-end workflows running through the new model

---

## 4. Proposed Runtime Shape

The minimal runtime shape should center around one entry point:

```python
run_action(...)
```

Recommended supported forms:

```python
run_action(dut="stm32f103_target_1", action="flash", request={...})
```

and

```python
run_action(instrument="esp_jtag_1", action="gpio_measure", request={...})
```

This should be the main AI-facing runtime API.

Everything else may remain internal.

---

## 5. Minimal Code Structure

A lightweight module layout could look like this:

```
ael/
  instruments/
    action_registry.py
    dispatcher.py
    result.py
    config_loader.py
    selection.py

    backends/
      esp_remote_jtag.py
      stlink.py
      usb_uart_bridge.py

    configs/
      instruments/
      duts/
```

This exact layout is not mandatory, but the functional separation is recommended.

---

## 6. Action Registry

### 6.1 Purpose

The action registry is the canonical list of supported action names and their basic contracts.

It should answer:

- what actions exist
- what request fields are expected
- what result data is usually returned
- what common error codes may appear

### 6.2 v0.1 action set

Recommended initial registry:

- `flash`
- `reset`
- `uart_read`
- `uart_wait_for`
- `gpio_measure`
- `voltage_read`
- `debug_halt`
- `debug_read_memory`

### 6.3 Suggested structure

A lightweight Python dictionary or dataclass-based registry is sufficient.

Example shape:

```python
ACTION_REGISTRY = {
    "flash": {
        "required_request_fields": ["firmware"],
        "optional_request_fields": ["format", "erase", "verify", "reset_after"],
    },
    "reset": {
        "required_request_fields": [],
        "optional_request_fields": ["mode"],
    },
    "uart_wait_for": {
        "required_request_fields": ["pattern"],
        "optional_request_fields": ["baud", "timeout_s"],
    },
    "gpio_measure": {
        "required_request_fields": ["channel"],
        "optional_request_fields": ["mode", "duration_s"],
    },
    "voltage_read": {
        "required_request_fields": ["channel"],
        "optional_request_fields": [],
    },
    "debug_halt": {
        "required_request_fields": [],
        "optional_request_fields": [],
    },
    "debug_read_memory": {
        "required_request_fields": ["address", "length"],
        "optional_request_fields": [],
    },
}
```

This does not need to be elaborate in v0.1.

### 6.4 Validation responsibility

The action registry should support lightweight validation:

- unknown action should fail clearly
- missing required request field should fail clearly
- unsupported action on selected instrument should fail clearly

---

## 7. Config Representation

### 7.1 Goals

The config model should be easy for both humans and AI to read.

It should express:

- DUT identity
- instrument identity
- supported actions
- attachment relationship
- connection parameters

### 7.2 DUT config example

```yaml
name: stm32f103_target_1
role: dut
attached_instruments:
  - stlink_1
  - usb_uart_1
  - esp_jtag_1
```

### 7.3 Instrument config example

```yaml
name: esp_jtag_1
role: instrument
driver: esp_remote_jtag
connection:
  host: 192.168.1.50
  port: 5555
supports:
  - flash
  - reset
  - gpio_measure
  - voltage_read
  - signal_capture
attached_to:
  - stm32f103_target_1
```

### 7.4 Config loader responsibilities

A config loader should:

- load DUT and instrument definitions
- build a lookup map by name
- support attached instrument resolution
- expose simple query methods

Example:

```python
catalog.get_dut("stm32f103_target_1")
catalog.get_instrument("esp_jtag_1")
catalog.get_attached_instruments("stm32f103_target_1")
```

---

## 8. Dispatcher

### 8.1 Purpose

The dispatcher is the central runtime engine for action execution.

It should:

- validate invocation arguments
- resolve DUT or instrument
- select a compatible instrument if needed
- validate request fields
- call backend implementation
- normalize result shape
- return structured success/failure

### 8.2 Suggested high-level flow

For DUT-oriented invocation:

```
run_action(dut=..., action=..., request=...)
  -> resolve DUT
  -> get attached instruments
  -> filter by supported action
  -> select instrument
  -> invoke backend
  -> normalize result
  -> return result
```

For instrument-oriented invocation:

```
run_action(instrument=..., action=..., request=...)
  -> resolve instrument
  -> verify supported action
  -> invoke backend
  -> normalize result
  -> return result
```

### 8.3 Selection policy

v0.1 should use a simple selection policy.

Recommended behavior:

- if one instrument matches, use it
- if multiple match, use fixed priority
- if none match, return structured failure

A future version may consider:

- reliability scores
- preferred instrument per action
- per-board policy
- per-workflow hints

But none of that is required for v0.1.

---

## 9. Result Normalization

### 9.1 Purpose

Backends may return different raw information.
The dispatcher or result helper should normalize that into one standard format.

### 9.2 Standard result fields

Recommended common fields:

- `ok`
- `action`
- `instrument`
- `dut`
- `summary`
- `data`
- `logs`

Recommended failure fields:

- `error_code`
- `message`
- `retryable`

### 9.3 Success example

```python
{
    "ok": True,
    "action": "flash",
    "instrument": "stlink_1",
    "dut": "stm32f103_target_1",
    "summary": "Flash completed successfully",
    "data": {"elapsed_s": 2.8},
    "logs": ["Connected", "Erase complete", "Program complete"],
}
```

### 9.4 Failure example

```python
{
    "ok": False,
    "action": "gpio_measure",
    "instrument": "esp_jtag_1",
    "dut": "stm32f103_target_1",
    "error_code": "measurement_failed",
    "message": "No valid toggle detected on channel ch1",
    "retryable": True,
    "logs": ["Channel opened", "No stable signal found"],
}
```

---

## 10. Backend Contract

### 10.1 Purpose

Each instrument backend should implement only the actions it supports.

The backend contract should stay lightweight.

Recommended pattern:

```python
backend.invoke(action="flash", request={...}, context={...})
```

or direct action methods:

```python
backend.flash(request, context)
backend.reset(request, context)
```

Either style is acceptable.
The simpler one for the current codebase should be chosen.

### 10.2 Backend responsibilities

A backend should:

- validate action-specific request details when necessary
- perform the real device operation
- capture useful logs
- return raw or normalized result data
- map known failures into structured errors if possible

### 10.3 Backend non-goals

Backends should not own global policy decisions such as:

- which instrument should be selected for a DUT
- workflow-level pass/fail judgment across multiple instruments
- global scheduling policy

Those belong above the backend level.

---

## 11. Recommended First Integration: ESP JTAG

### 11.1 Why ESP JTAG first

ESP JTAG should be the first major integration because:

- it is currently the least abstracted / least packaged of the important tools
- it is strategically important for the product direction
- it validates the multi-action instrument concept strongly
- it forces the model to handle more than just narrow single-purpose tools

### 11.2 Recommended first action subset

For the first ESP JTAG integration, start with:

- `flash`
- `reset`
- `gpio_measure`

Optional next additions:

- `voltage_read`
- `signal_capture`

This is enough to prove the value of the new model.

### 11.3 Success condition for ESP JTAG integration

ESP JTAG integration is successful when a real DUT workflow can do all of the following through the new action model:

- flash firmware
- reset DUT
- measure a GPIO behavior
- return structured results

---

## 12. Recommended Second Integrations

After ESP JTAG, integrate one or both of:

- ST-Link
- USB-UART bridge

### 12.1 ST-Link target actions

Recommended initial actions:

- `flash`
- `reset`
- `debug_halt`
- `debug_read_memory`

### 12.2 USB-UART target actions

Recommended initial actions:

- `uart_read`
- `uart_wait_for`

These two integrations will validate the narrow/specialized instrument side of the model.

---

## 13. Wiring and Binding Data

### 13.1 Principle

Wiring and channel mapping are important, but should remain mostly support data in v0.1.

The main runtime model should not require the AI to reason deeply about them for every action.

### 13.2 Recommended handling

Allow configs to carry extra setup data such as:

```yaml
connections:
  swd: connected
  nrst: connected
  gpio_channels:
    ch1: pa0
  voltage_channels:
    vcc: 3v3
```

Backends may consume these fields internally.

This allows the action model to stay simple while preserving the information needed for setup and troubleshooting.

---

## 14. Representative Implementation Phases

### Phase 1: Registry + Config + Dispatcher Skeleton

Deliverables:

- action registry
- config loader
- dispatcher function
- result helper
- stub backend interface

Success criteria:

- `run_action(...)` exists
- config can be loaded
- unsupported or invalid invocations fail cleanly

### Phase 2: ESP JTAG initial integration

Deliverables:

- ESP JTAG backend
- support for `flash`
- support for `reset`
- support for `gpio_measure`

Success criteria:

- one real DUT workflow runs through the new model

### Phase 3: ST-Link and/or USB-UART integration

Deliverables:

- ST-Link backend or adapter
- USB-UART backend or adapter

Success criteria:

- one multi-instrument DUT workflow runs through the new model

### Phase 4: Real workflow validation and cleanup

Deliverables:

- run at least two real workflows
- inspect friction points
- adjust field names, result shapes, and config patterns
- document lessons learned

Success criteria:

- the model feels easier and more natural than the old implicit approach

---

## 15. Recommended Real Validation Workflows

The following real workflows are recommended to validate the implementation.

**Workflow A: STM32 + ESP JTAG**

- flash via `flash`
- reset via `reset`
- verify output frequency via `gpio_measure`

**Workflow B: STM32 + ST-Link + USB-UART**

- flash via `flash`
- reset via `reset`
- wait for serial banner via `uart_wait_for`

**Workflow C: One DUT, mixed evidence**

- flash through one instrument
- read UART through another
- measure GPIO through another
- combine evidence at the workflow level

These workflows are more important than synthetic tests.

---

## 16. Suggested Python Interfaces

These are examples, not mandatory API freeze points.

### 16.1 Dispatcher

```python
def run_action(*, dut=None, instrument=None, action, request):
    ...
```

### 16.2 Catalog

```python
catalog.get_dut(name)
catalog.get_instrument(name)
catalog.get_attached_instruments(dut_name)
```

### 16.3 Selection

```python
select_instrument_for_action(dut_name, action, catalog)
```

### 16.4 Result helpers

```python
make_success_result(action, instrument, dut, summary, data, logs)
make_error_result(action, instrument, dut, error_code, message, retryable, logs)
```

Keep these helpers explicit and simple.

---

## 17. Migration Guidance

### 17.1 Do not try to refactor everything at once

The safest path is to wrap existing working code gradually.

Example:

- keep existing ST-Link logic
- add a thin adapter that exposes `flash` / `reset`
- let the dispatcher call through the adapter

This reduces risk.

### 17.2 Favor adapters over deep rewrites

If current code already works, prefer:

- thin integration layer
- standard result conversion
- request normalization

rather than a deep immediate rewrite.

### 17.3 Let real usage drive cleanup

After two or three real workflows are running, the code shape will become clearer.
That is the right time to improve naming, config shape, and policy behavior.

---

## 18. Risks and Failure Modes

### 18.1 Over-abstraction risk

If the implementation tries to build a perfect universal framework too early, delivery will slow and the AI-facing model may become harder to use.

Mitigation:

- keep v0.1 small
- prioritize real workflows
- prefer simple adapters

### 18.2 Under-structured results risk

If backends return inconsistent raw text, the AI will have a harder time making decisions.

Mitigation:

- enforce one common result shape early

### 18.3 Premature scheduler complexity

If selection logic becomes complex too early, debugging will become harder.

Mitigation:

- fixed priority is enough for v0.1

### 18.4 Setup ambiguity risk

If connection/binding data stays too implicit, actions may succeed/fail unpredictably.

Mitigation:

- keep wiring support data in config
- surface it clearly during troubleshooting

---

## 19. Definition of Done for v0.1

Instrument Action implementation v0.1 is considered done when:

- action registry exists
- config loader exists
- dispatcher exists
- standard result format exists
- ESP JTAG runs at least one real workflow through the new model
- at least one narrow/specialized instrument is integrated
- at least one multi-instrument DUT workflow runs through the new model
- the new model is judged practically easier for AI use than the previous shape

---

## 20. Summary

The implementation plan for v0.1 is intentionally pragmatic.

It does not aim to create a perfect abstraction framework.
It aims to create a simple and useful AI-facing action model that works on real hardware now.

Recommended order:

1. action registry
2. config model
3. dispatcher
4. result normalization
5. ESP JTAG first
6. ST-Link / USB-UART next
7. validate on real workflows
8. evolve from evidence
