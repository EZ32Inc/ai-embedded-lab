# ESP32-JTAG Action Mapping v0.1

Date: 2026-03-18
Status: Active Draft

## Purpose

This document maps IAM actions onto the ESP32-JTAG reference instrument.

It defines:

- which actions are in scope now
- which are deferred
- request expectations
- normalized result expectations
- backend ownership boundaries

This document is execution-oriented. It should be used while implementing the reference backend.

Parent document:

- [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md)

## Scope

### Phase 1 actions

- `flash`
- `reset`
- `gpio_measure`

### Phase 2 actions

- `debug_halt`
- `debug_read_memory`

### Explicitly not required for initial reference completion

- `uart_read`
- `uart_wait_for`
- `voltage_read`
- `signal_capture`
- arbitrary instrument-specific action names

## Action Mapping Table

| IAM action | Phase | ESP32-JTAG role | Primary transport command | Result focus |
|---|---|---|---|---|
| `flash` | 1 | program DUT firmware | `flash` | programming outcome |
| `reset` | 1 | reset DUT | `reset` | reset completion |
| `gpio_measure` | 1 | inspect DUT GPIO behavior | `gpio_measure` | measured values + summary |
| `debug_halt` | 2 | stop target execution | `debug_halt` | halt state |
| `debug_read_memory` | 2 | read target memory | `debug_read_memory` | address/length/data |

## Action Contracts

### `flash`

#### Intent

Program firmware to the DUT through the ESP32-JTAG path.

#### Minimum request

```json
{
  "firmware_path": "build/app.elf",
  "target": "stm32f103"
}
```

#### Common optional fields

- `options.erase`
- `options.verify`
- `options.reset_after`

#### Backend behavior

1. validate request
2. check firmware path exists
3. send normalized transport request
4. map device response into IAM success or failure

#### Success shape

```json
{
  "status": "success",
  "action": "flash",
  "data": {
    "firmware_path": "build/app.elf",
    "target": "stm32f103",
    "bytes_written": 12345,
    "elapsed_s": 2.4,
    "verified": true
  },
  "logs": []
}
```

#### Failure codes

- `invalid_request`
- `transport_unavailable`
- `request_timeout`
- `device_busy`
- `programming_failure`

### `reset`

#### Intent

Bring the DUT back into a known state.

#### Minimum request

```json
{
  "reset_kind": "hard"
}
```

#### Allowed reset kinds

- `hard`
- `soft`
- `line`

#### Success focus

- reset method used
- elapsed time

#### Failure codes

- `invalid_request`
- `transport_unavailable`
- `request_timeout`
- `device_busy`
- `reset_failure`

### `gpio_measure`

#### Intent

Use the ESP32-JTAG measurement capability to inspect DUT GPIO behavior.

#### Minimum request

```json
{
  "channels": ["PA0"],
  "measurement_type": "signature"
}
```

#### Common optional fields

- `settle_ms`
- `duration_ms`
- mode-specific thresholds or expected ranges

#### Recommended measurement types for v0.1

- `signature`
- `frequency`
- `logic_level`

#### Success focus

- channels observed
- measured values
- normalized summary
- optional `pass_hint`

#### Failure codes

- `invalid_request`
- `transport_unavailable`
- `request_timeout`
- `device_busy`
- `measurement_failure`

### `debug_halt`

#### Status

Phase 2 placeholder action.

#### Intent

Stop target execution at a controlled point.

#### Expected output

- halted status
- optional PC/register summary
- elapsed time

#### Minimum requirement for first implementation

Even before full semantics, the action should return the standard shape and explicit unsupported/failure outcomes.

### `debug_read_memory`

#### Status

Phase 2 placeholder action.

#### Intent

Read a bounded memory range from the DUT.

#### Minimum request

```json
{
  "address": "0x20000000",
  "length": 64
}
```

#### Expected output

- normalized address
- requested length
- returned bytes or representation
- clear failure if address/read cannot be performed

## Ownership Boundaries

### Backend owns

- action dispatch
- supported action list
- exception normalization
- final IAM result shape

### Transport owns

- socket/session communication
- timeout and connection behavior
- request/response framing

### Action handler owns

- request validation
- transport command payload mapping
- backend response interpretation
- normalized success data fields

### Action handler does not own

- connection lifecycle policy
- global backend registry policy
- high-level AEL workflow decisions

## Mapping Rules

### Rule 1: no action renaming

Do not invent names like:

- `program_firmware`
- `reset_target`
- `capture_gpio_signature`

Use the IAM standard names.

### Rule 2: transport commands may differ from IAM names

The external device protocol may use the same command names, but that is not required.
The public backend contract is the IAM action name.

### Rule 3: no raw device response leakage

Raw device payload can be logged, but the returned result should be normalized.

### Rule 4: failure contract matters as much as success contract

ESP32-JTAG is the reference implementation, so structured failure is mandatory.

## Open Items

- decide exact payload shape for `gpio_measure` thresholds and expectations
- decide whether `target` is mandatory for all `flash` calls or can be implied from binding
- decide whether `debug_halt` and `debug_read_memory` should ship as explicit unsupported placeholders first
- decide whether `voltage_read` should be promoted into the reference scope after Phase 1

