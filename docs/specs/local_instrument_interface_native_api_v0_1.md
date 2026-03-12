# Local Instrument Interface Native API v0.1

## Purpose

This document records the current bounded Local Instrument Interface / Instrument Native API contract that is now proven in the repository.

It is intentionally small.

## Position

This is the lower local layer of the agreed two-layer instrument model.

It is:

- local or LAN-facing
- instrument-native
- independent of future cloud registration/session infrastructure

## Current Proven Shape

The current proven pilot is:

- `usb_uart_bridge_daemon`

The current additive follow-on pilot is:

- `esp32s3_dev_c_meter`

## Metadata Commands

Current bounded metadata command set:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

These commands should describe:

- stable identity
- protocol version
- capability set
- present/usable state
- doctor/health details

## Action Commands

Action commands are capability-specific.

They are not required to be identical across all instruments.

Current proven UART-bridge actions:

- `open`
- `close`
- `write_uart`
- `read_uart`

Current meter-aligned candidate actions:

- `measure_digital`
- `measure_voltage`
- `stim_digital`

Current meter and bridge implementations now share:

- protocol:
  - `ael.local_instrument.native_api.v0.1`
- metadata command vocabulary
- success/error response envelope shape

## Response Model

Current bounded response model:

Success:

```yaml
status: ok
data: ...
```

Error:

```yaml
status: error
error:
  code: string
  message: string
  retryable: bool
```

Optional details may be added where useful.

## Important Boundary

The Local Instrument Interface should expose native actions only.

It should not expose higher-level verification verdicts such as:

- signature match / mismatch
- DUT behavior pass/fail
- orchestration-level task verdicts

Those remain above this layer.

## Relation to Existing AEL Surfaces

This lower-layer API should remain compatible with:

- instrument manifests
- capability metadata
- `instrument_view`
- `instrument_doctor`

It should not require a broad runtime rewrite to be useful.

## Non-Goals

This document does not define:

- cloud registration
- cloud sessions
- auth/ownership
- complete control-instrument unification

## Recommended Next Use

The next safe use is:

- continue applying this lower-layer shape selectively
- use `default veri` as a regression gate whenever shared instrument surfaces are touched

## Current Stop Point

At the current stop point:

- bridge pilot is the strongest lower-layer example
- meter pilot is additive and useful
- control-instrument normalization is still intentionally deferred
