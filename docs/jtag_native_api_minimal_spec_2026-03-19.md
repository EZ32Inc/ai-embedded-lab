# JTAG Native API Minimal Spec

Date: 2026-03-19

## Purpose

Define the minimum viable `jtag_native_api` surface for `ESP32JTAG` as a
first-class multi-capability instrument.

This is a specification memo only.

## Design Goal

`jtag_native_api` should define instrument identity and instrument-level
metadata/status/doctor semantics.

It should **not** replace the `esp32_jtag` backend action package.

Recommended split:

- `jtag_native_api`:
  - identity
  - capabilities
  - status
  - doctor
  - minimal instrument-level actions
- `esp32_jtag backend`:
  - action execution
  - runtime transport details

## Protocol Envelope

Protocol string:

- `ael.local_instrument.jtag_native_api.v0.1`

Response model:

- success:
  - `{"status": "ok", "data": {...}}`
- error:
  - `{"status": "error", "error": {"code": "...", "message": "...", "retryable": bool}}`

## Identity Payload

Recommended `identify(...)` payload:

```json
{
  "device_id": "esp32jtag_stm32f411",
  "device_type": "multi_capability_instrument",
  "instrument_family": "esp32jtag",
  "model": "ESP32JTAG",
  "protocol_version": "ael.local_instrument.jtag_native_api.v0.1",
  "communication_endpoints": {
    "debug_remote": "192.168.2.103:4242",
    "control_api": "https://192.168.2.103:443"
  },
  "capability_families": [
    "debug_remote",
    "capture_control",
    "reset_control"
  ]
}
```

## Capabilities Payload

Recommended `get_capabilities(...)` payload:

```json
{
  "protocol_version": "ael.local_instrument.jtag_native_api.v0.1",
  "capability_families": {
    "debug_remote": {
      "actions": ["flash", "debug_halt", "debug_read_memory"],
      "transport": "gdb_remote"
    },
    "reset_control": {
      "actions": ["reset"]
    },
    "capture_control": {
      "actions": ["gpio_measure"],
      "transport": "control_api"
    }
  }
}
```

This surface should describe families first, not only flat action names.

## Status Payload

Recommended `get_status(...)` payload:

```json
{
  "protocol_version": "ael.local_instrument.jtag_native_api.v0.1",
  "reachable": true,
  "endpoints": {
    "debug_remote": {"ok": true},
    "control_api": {"ok": true}
  },
  "health_domains": {
    "network": {"ok": true},
    "debug_remote": {"ok": true},
    "capture_control": {"ok": true}
  }
}
```

## Doctor Payload

Recommended `doctor(...)` payload:

```json
{
  "protocol_version": "ael.local_instrument.jtag_native_api.v0.1",
  "reachable": true,
  "checks": {
    "network": {"ok": true},
    "debug_remote": {"ok": true},
    "target_enumeration": {"ok": true},
    "capture_control": {"ok": true}
  }
}
```

The exact checks may vary, but the object shape should remain stable.

## Minimal Action Commands

`jtag_native_api` should expose only a minimal instrument-level action list.

Recommended minimal list:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `preflight_probe`

Optional early additions:

- `capture_signature`
- `program_firmware`

The important boundary rule:

- if an action is already cleanly owned by `esp32_jtag backend`, it does not
  need to move into `jtag_native_api`

## Non-Goals

This minimal spec does not require:

- replacing dispatcher routing
- replacing `esp32_jtag backend`
- removing `control_instrument_native_api` immediately
- redefining the full preflight implementation

## Conclusion

The minimal `jtag_native_api` should be a first-class instrument interface
layer, not a duplicate action backend.

Its job is to make `ESP32JTAG` legible as a named multi-capability instrument.
