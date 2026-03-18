# ESP32-JTAG Validation Plan v0.1

Date: 2026-03-18
Status: Active Draft

## Purpose

This document defines how to validate the ESP32-JTAG reference instrument.

The target is not just "it works once."
The target is:

- IAM contract correctness
- repeatable backend behavior
- useful failure structure
- enough confidence for other instruments to align to it

Parent document:

- [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md)

Related execution doc:

- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)

## Validation Goals

ESP32-JTAG is considered reference-ready only if it proves:

1. action names are IAM-aligned
2. success shape is stable
3. failure shape is stable
4. repeated runs are reliable
5. the implementation is reusable as the alignment template

## Validation Scope

### Phase 1 required actions

- `flash`
- `reset`
- `gpio_measure`

### Phase 2 follow-up actions

- `debug_halt`
- `debug_read_memory`

## Validation Layers

### Layer A: Structural validation

Check:

- supported actions are explicitly declared
- unsupported action returns structured failure
- request validation failures are structured
- success result shape matches contract
- failure result shape matches contract

### Layer B: Smoke validation

Minimum smoke path:

1. flash DUT
2. reset DUT
3. measure known GPIO behavior

Minimum outcome:

- all three actions succeed in one end-to-end flow
- no unstructured errors

### Layer C: Stability validation

Run the same working flow repeatedly.

Recommended threshold:

- at least `5` consecutive pass runs for initial milestone

Preferred stronger threshold after first success:

- `10` consecutive passes

### Layer D: Failure-path validation

Each of the following should produce structured failure:

- instrument unavailable
- timeout
- bad request field
- unsupported action
- device busy
- hardware-side operation failure

### Layer E: Integration validation

Confirm that the backend is usable through AEL integration, not only via an isolated smoke script.

Minimum integration target:

- one real AEL smoke path using ESP32-JTAG as the active instrument

## Suggested Test Matrix

| Category | Case | Expected outcome |
|---|---|---|
| structural | unsupported action | structured failure |
| structural | missing required field | structured failure |
| smoke | `flash -> reset -> gpio_measure` | pass |
| stability | repeat smoke path 5x | all pass |
| failure | device unreachable | `transport_unavailable` or equivalent |
| failure | timeout | `request_timeout` |
| failure | invalid `reset_kind` | `invalid_request` |
| failure | invalid firmware path | `invalid_request` |
| failure | measurement operation fails | `measurement_failure` |

## Action-Specific Checks

### `flash`

Validate:

- valid image path passes
- missing image path fails structurally
- nonexistent image path fails structurally
- backend programming failure is normalized

### `reset`

Validate:

- each allowed reset kind maps cleanly
- invalid reset kind fails structurally
- backend reset failure is normalized

### `gpio_measure`

Validate:

- non-empty channel list required
- channel request is passed correctly to transport
- success includes `channels`, `values`, `summary`
- backend measurement failure is normalized

### `debug_halt`

When enabled:

- success shape exists
- unsupported or unavailable behavior is still structured

### `debug_read_memory`

When enabled:

- address/length validation is explicit
- invalid read returns structured failure
- output shape is bounded and deterministic

## Acceptance Criteria

ESP32-JTAG passes the validation plan when:

1. Phase 1 actions exist and are callable
2. all Phase 1 success paths return normalized success shape
3. all tested failure paths return normalized failure shape
4. smoke path passes on real hardware
5. repeated smoke runs meet the chosen stability threshold
6. backend structure remains consistent with the backend skeleton doc

## Exit Conditions

### Phase 1 complete

All of these are true:

- `flash`, `reset`, `gpio_measure` implemented
- smoke path passes
- at least 5 repeated passes
- structured failure cases demonstrated

### Reference-ready

All of these are true:

- Phase 1 complete
- code structure matches the skeleton well enough to serve as template
- docs are clear enough for other backend alignment
- at least one future backend can be aligned against it without changing IAM rules

## Non-Goals

This plan does not require:

- every possible future action to be implemented now
- full AI behavior test coverage in the same milestone
- ST-Link and USB-UART to be aligned before ESP32-JTAG is stable

## Recommended Execution Order

1. finish backend skeleton
2. implement `flash`
3. implement `reset`
4. implement `gpio_measure`
5. run structural tests
6. run one smoke path
7. run repeated stability path
8. run failure-path checks
9. integrate into AEL path
10. only then start alignment of other instruments

