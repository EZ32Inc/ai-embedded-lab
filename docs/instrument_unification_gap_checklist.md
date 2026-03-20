# Instrument Unification Gap Checklist

Status legend:

- `OK`: contract is aligned with instrument model v1 for the checked area
- `PARTIAL`: usable, but still leaks legacy or has semantic mismatch
- `BROKEN`: not aligned enough to rely on the model

## ST-Link

- `identify`: PARTIAL
  - returns legacy native profile naming in protocol metadata
- `get_capabilities`: PARTIAL
  - capability families exist but not mapped to stable taxonomy names
- `get_status`: PARTIAL
  - health domains are family-local, not taxonomy-backed
- `doctor`: PARTIAL
  - doctor schema differs from meter and uart families
- `preflight_probe`: PARTIAL
  - action semantics are usable, but response shape is legacy-first
- `program_firmware`: PARTIAL
  - unified envelope added in interface layer; legacy backend still underneath
- naming consistency: PARTIAL
  - still leaks `stlink_native_api` in lower layers
- error consistency: PARTIAL
  - good retryability, but error codes not yet taxonomized

## ESP32 JTAG

- `identify`: PARTIAL
  - family is correct, but capability names are still family-local
- `get_capabilities`: PARTIAL
  - capability families exist but not yet mapped to taxonomy strings
- `get_status`: PARTIAL
  - domain structure differs from ST-Link and meter
- `doctor`: PARTIAL
  - semantically rich but not fully normalized
- `preflight_probe`: PARTIAL
  - useful but legacy-first response
- `program_firmware`: PARTIAL
  - unified envelope added in interface layer; legacy backend still underneath
- `capture_signature`: PARTIAL
  - action exists but still returns legacy payload shape
- naming consistency: PARTIAL
  - still leaks `jtag_native_api` below interface layer
- error consistency: PARTIAL
  - no single family-independent error taxonomy yet

## ESP32 Meter

- `identify`: PARTIAL
  - manifest-side contract differs from control-side families
- `get_capabilities`: PARTIAL
  - capability declaration uses instrument-specific names like `measure.digital`
- `get_status`: PARTIAL
  - health semantics differ from doctor and from control instruments
- `doctor`: PARTIAL
  - envelope is legacy-first
- `measure_digital`: PARTIAL
  - action contract not yet wrapped to model v1 envelope
- `measure_voltage`: PARTIAL
  - same mismatch as digital measure
- `stim_digital`: PARTIAL
  - same mismatch as digital measure
- naming consistency: PARTIAL
  - lower layer still exposes `meter_native_api`
- error consistency: PARTIAL
  - errors are usable but not taxonomy-backed

## USB UART Bridge

- `identify`: PARTIAL
  - largely aligned but still bridge-specific terminology
- `get_capabilities`: PARTIAL
  - capability groups are not yet taxonomy-backed (`uart.bridge`, `uart.observe` should be explicit)
- `get_status`: PARTIAL
  - health domains are simple and not normalized with other families
- `doctor`: PARTIAL
  - lifecycle info present, but response semantics differ from others
- `open`: PARTIAL
  - action payload shape is legacy-first
- `close`: PARTIAL
  - same mismatch as `open`
- `write_uart`: PARTIAL
  - no strict request/result model yet
- `read_uart`: PARTIAL
  - no strict request/result model yet
- naming consistency: PARTIAL
  - lower layer still exposes `usb_uart_bridge_daemon`
- error consistency: PARTIAL
  - HTTP errors wrapped, but not classified under shared boundaries

## Cross-Cutting Summary

- unified provider spine: OK
- unified dispatch routing: OK
- unified action envelope: PARTIAL
- stable capability taxonomy: BROKEN
- normalized doctor/status semantics: BROKEN
- reporting vocabulary: PARTIAL
- fallback/degradation model: PARTIAL
