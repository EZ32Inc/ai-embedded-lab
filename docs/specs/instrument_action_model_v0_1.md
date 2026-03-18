# Instrument Action Model v0.1

## Status

Draft

## Related Documents

- [instrument_action_examples_v0_1.md](instrument_action_examples_v0_1.md) — concrete workflow examples
- [instrument_action_implementation_plan_v0_1.md](instrument_action_implementation_plan_v0_1.md) — recommended implementation plan

---

## Purpose

This document defines a lightweight, AI-friendly instrument abstraction model for AEL.

The goal is **not** to build a heavy, human-first device framework.
The goal is to give an AI agent a simple, stable way to:

- discover available instruments
- understand what each instrument can do
- select instruments by action
- combine multiple instruments around one DUT
- execute actions with predictable results

This model is intentionally **action-first** and **workflow-first**.

---

## 1. Design Goals

The instrument abstraction should help AEL support real hardware workflows such as:

- flash firmware to a DUT
- reset a DUT
- read or wait for UART output
- measure GPIO behavior
- read DUT voltage
- perform limited debug access

The design priorities are:

1. **AI-first usability**
   - The model should be easy for an AI agent to understand and use.
   - It should expose a small number of concepts.
   - It should make action selection obvious.

2. **Action-first abstraction**
   - The main question is not "what kind of device is this?"
   - The main question is "what actions can this device perform?"

3. **Support real workflows**
   - The abstraction must work for already-proven AEL scenarios.
   - It must support both single-instrument and multi-instrument DUT workflows.

4. **Allow implementation diversity**
   - ST-Link, ESP JTAG, USB-UART, and future instruments do not need to share the same internal implementation.
   - They only need to present a common action surface and common result shape.

5. **Stay lightweight**
   - v0.1 should avoid unnecessary layering and over-generalization.
   - Internal implementation can evolve later without changing the AI-facing model.

---

## 2. Core Concepts

v0.1 intentionally uses only three primary concepts.

### 2.1 Device

A real hardware entity.

Examples:

- an STM32 board
- an ESP32 board
- an ST-Link
- a USB-UART bridge
- an ESP-based JTAG/measurement box

A device is a physical thing, not a role.

---

### 2.2 Role

A device participates in a workflow with a current role.

Supported roles in v0.1:

- `dut`
- `instrument`

A device type may appear in different roles in different workflows.

Example:

- An ESP32 board may be a DUT in one workflow.
- The same kind of ESP32 board may be an instrument/helper board in another workflow.

v0.1 does **not** require simultaneous multi-role behavior in the same workflow.

---

### 2.3 Action

An action is a standard operation that an AI agent can request.

Examples:

- `flash`
- `reset`
- `uart_read`
- `uart_wait_for`
- `gpio_measure`
- `voltage_read`
- `debug_halt`
- `debug_read_memory`

Actions are the primary abstraction boundary in this model.

---

## 3. AI-Facing Model

The AI should mainly see:

1. what DUT is being worked on
2. what instruments are attached to that DUT
3. what actions each instrument supports
4. a single standard way to run an action
5. a single standard result format

The AI should **not** need to reason about deep driver structure during normal operation.

---

## 4. Supported Actions in v0.1

### 4.1 Required Actions

The initial recommended action set for v0.1 is:

- `flash`
- `reset`
- `uart_read`
- `uart_wait_for`
- `gpio_measure`
- `voltage_read`
- `debug_halt`
- `debug_read_memory`

These actions are sufficient to support many AEL bring-up, smoke-test, and verification workflows.

---

### 4.2 Optional / Future Actions

These are explicitly out of scope for minimal v0.1, but the model should leave room for them:

- `debug_run`
- `signal_capture`
- `signal_generate`
- `power_on`
- `power_off`
- `set_boot_mode`
- `usb_enumerate`
- `adc_read`
- `spi_transfer`
- `i2c_scan`

---

## 5. Action Semantics

This section defines the expected meaning of each v0.1 action.

---

### 5.1 `flash`

Programs firmware to the DUT.

Typical usage:

- ELF/BIN/HEX programming
- optional erase
- optional verification
- optional reset after programming

Minimum request:

- `firmware`

Common optional fields:

- `format`
- `erase`
- `verify`
- `reset_after`

Expected outcome:

- programming succeeds or fails clearly
- elapsed time may be reported
- relevant logs may be included

---

### 5.2 `reset`

Resets the DUT into a known state.

Typical usage:

- reset after flash
- reset before measurement
- recover from test state

Minimum request:

- none required, unless mode selection is needed

Common optional fields:

- `mode`

Expected outcome:

- DUT reset command completed or failed clearly

---

### 5.3 `uart_read`

Reads UART output for a defined period or under defined conditions.

Typical usage:

- capture banner output
- collect runtime logs
- inspect boot messages

Common request fields:

- `baud`
- `duration_s`

Expected outcome:

- captured text
- timing/log information if useful

---

### 5.4 `uart_wait_for`

Waits until UART output contains a given pattern, or timeout occurs.

Typical usage:

- wait for `"Hello"`
- wait for `"PASS"`
- wait for boot complete text

Minimum request:

- `pattern`

Common optional fields:

- `baud`
- `timeout_s`

Expected outcome:

- match success/failure
- matched text or capture excerpt
- timeout handling

---

### 5.5 `gpio_measure`

Measures a GPIO or digital signal channel.

Typical usage:

- detect static high/low
- detect toggle activity
- estimate frequency
- validate a known signal signature

Common request fields:

- `channel`
- `mode`
- `duration_s`

Representative modes may include:

- `level`
- `toggle`
- `frequency`
- `signature`

Expected outcome:

- measured result
- interpretation summary
- raw or semi-raw evidence when available

---

### 5.6 `voltage_read`

Reads a voltage channel associated with a DUT or instrument.

Typical usage:

- confirm DUT power presence
- confirm expected rail level
- assist with power/debug diagnosis

Common request fields:

- `channel`

Expected outcome:

- measured voltage value
- optional unit and tolerance interpretation

---

### 5.7 `debug_halt`

Halts the DUT CPU through a debug-capable instrument.

Typical usage:

- pause execution
- prepare for memory inspection

Expected outcome:

- halt success/failure

---

### 5.8 `debug_read_memory`

Reads memory through a debug-capable instrument.

Typical usage:

- inspect RAM/mailbox state
- confirm status flags
- support debug-oriented verification

Minimum request:

- `address`
- `length`

Expected outcome:

- returned data bytes or decoded representation
- clear indication of success/failure

---

## 6. Instrument Representation

An instrument in v0.1 should declare:

1. identity
2. role
3. driver/backend
4. connection information
5. supported actions
6. optional DUT attachment

Example:

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

This is intentionally simple.

The AI should not need to know more than this during normal operation.

---

## 7. DUT Representation

A DUT in v0.1 should declare:

1. identity
2. role
3. attached instruments

Example:

```yaml
name: stm32f103_target_1
role: dut
attached_instruments:
  - stlink_1
  - usb_uart_1
  - esp_jtag_1
```

This gives the AI a clear resource map.

---

## 8. Standard Invocation Model

The system should provide a common action execution entry point.

Two usage patterns are supported.

### 8.1 DUT-Oriented Invocation

The AI specifies a DUT and an action.
The system selects a compatible attached instrument.

Example:

```yaml
run_action:
  dut: stm32f103_target_1
  action: flash
  request:
    firmware: build/app.elf
```

This is the preferred default mode for AI workflows.

### 8.2 Instrument-Oriented Invocation

The AI explicitly selects an instrument.

Example:

```yaml
run_action:
  instrument: stlink_1
  action: flash
  request:
    firmware: build/app.elf
```

This is useful when:

- a specific instrument is preferred
- there are multiple matching instruments
- the AI is debugging the workflow itself

---

## 9. Instrument Selection Rules

When an action is invoked by DUT, the system should:

1. find the DUT's attached instruments
2. filter to those supporting the requested action
3. choose one compatible instrument
4. execute the action
5. return the standard result

v0.1 may use a simple selection strategy:

- if exactly one instrument matches, use it
- if multiple instruments match, use fixed priority
- later versions may use preference scores, reliability, or policy

---

## 10. Standard Result Format

Every action must return a predictable result structure.

Successful example:

```yaml
ok: true
action: flash
instrument: stlink_1
dut: stm32f103_target_1
summary: Flash completed successfully
data:
  elapsed_s: 2.8
logs:
  - Connected to target
  - Erase complete
  - Program complete
```

Failure example:

```yaml
ok: false
action: flash
instrument: stlink_1
dut: stm32f103_target_1
error_code: connection_timeout
message: Failed to connect to target within 5 seconds
retryable: true
logs:
  - Attempt 1 failed
```

This standard result format is important because AI agents depend on clear, structured outcomes.

---

## 11. Error Model

Every action implementation should map failures into a structured form.

Recommended fields:

- `ok`
- `error_code`
- `message`
- `retryable`
- `logs`

Representative error codes may include:

- `connection_timeout`
- `not_supported`
- `invalid_request`
- `program_failed`
- `verify_failed`
- `pattern_not_found`
- `measurement_failed`
- `target_not_halted`

v0.1 does not require a fully standardized global error catalog, but structured errors are required.

---

## 12. Wiring and Binding

Wiring and binding are real and important, but in v0.1 they are treated mostly as internal support data rather than primary AI-facing abstractions.

Internal examples may include:

```yaml
connections:
  stlink_1:
    swd: connected
    nrst: connected
  usb_uart_1:
    tx: pa10
    rx: pa9
  esp_jtag_1:
    ch1: pa0
    vcc: 3v3
```

Normal AI workflows should not need to reason about this level unless troubleshooting or setup verification is required.

Principle:

- keep wiring/binding in the system
- keep it available for debugging
- avoid making it the main abstraction surface for everyday AI actions

---

## 13. Role Switching

This model allows the same kind of hardware to appear in different roles in different workflows.

Example:

- `esp32s3_board_a` may be a DUT in one workflow
- `esp32s3_board_a` may be an instrument/helper in another workflow

This is acceptable because role is contextual, not intrinsic.

v0.1 does not require support for one live workflow where the same device actively participates in multiple roles at once.

---

## 14. Minimal v0.1 Implementation Scope

The recommended minimum implementation scope is:

- define the standard action list
- define instrument config format
- define DUT config format
- implement one common `run_action(...)` path
- support standard result formatting
- connect at least one multi-action instrument
- connect at least one single- or narrow-action instrument

Recommended first integrations:

- ESP JTAG box as the first multi-action example
- ST-Link and/or USB-UART as narrow/specialized examples

---

## 15. Recommended Migration Path

**Step 1** — Define the action registry and action contracts.

**Step 2** — Define the YAML/JSON representation for DUTs and instruments.

**Step 3** — Implement the central action dispatcher.

**Step 4** — Integrate ESP JTAG into the new action model.

**Step 5** — Integrate ST-Link and USB-UART.

**Step 6** — Use real workflows to validate whether the abstraction is natural and sufficient.

---

## 16. Success Criteria

This abstraction is considered successful if:

- the AI can quickly see what instruments are available
- the AI can select tools by action without confusion
- one DUT can naturally use multiple instruments in one workflow
- multi-function instruments fit naturally
- single-function instruments also fit naturally
- role switching across workflows does not break the model
- the model is easier to use than the previous implicit/driver-specific shape

---

## 17. Non-Goals for v0.1

The following are explicitly not required for v0.1:

- a perfect universal device framework
- exhaustive support for all lab instruments
- complete abstraction of all low-level debug capabilities
- simultaneous multi-role runtime for a single device
- advanced scheduler/policy logic
- a complete hardware graph engine

These may be future evolution areas, but they are not needed to validate the core model.

---

## 18. Summary

Instrument Action Model v0.1 is a deliberately lightweight, AI-first abstraction.

It standardizes:

- a small set of actions
- simple DUT/instrument declarations
- a common action invocation path
- a common result format

It does not attempt to over-engineer the internals.

The expected benefit is that AEL becomes easier for AI agents to operate, easier to extend with new instruments, and more natural for real hardware workflows.
