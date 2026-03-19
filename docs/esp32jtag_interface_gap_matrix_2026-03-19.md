# ESP32JTAG Interface Gap Matrix

Date: 2026-03-19

## Purpose

Compare the target instrument-level interface model for `ESP32JTAG` against the
current implementation boundary.

References:

- [docs/esp32jtag_instrument_interface_model_memo_2026-03-19.md](/nvme1t/work/codex/ai-embedded-lab/docs/esp32jtag_instrument_interface_model_memo_2026-03-19.md)
- [ael/instruments/control_instrument_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/control_instrument_native_api.py)
- [ael/instruments/backends/esp32_jtag/backend.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag/backend.py)

## Summary

The main gap is not action execution.

The main gap is that `ESP32JTAG` still lacks a first-class instrument-level
interface boundary with its own identity and multi-capability model.

## Gap Matrix

| Surface | Target Model | Current State | Gap |
|---|---|---|---|
| Instrument identity | `multi_capability_instrument`, family=`esp32jtag` | generic `control_instrument` | real gap |
| Metadata | explicit instrument-family metadata | generic control metadata only | real gap |
| Capability declaration | multiple capability families under one identity | partial generic observe/capture declaration + backend action capabilities | partial gap |
| Status | instrument-family specific status domains | generic `present=True` style status | real gap |
| Doctor | instrument-family specific doctor with multi-surface health | generic preflight-backed doctor | partial gap |
| Action execution | flash/reset/debug/capture actions | already present through `esp32_jtag` backend | no major gap |
| Transport model | explicit multi-endpoint model | implicit through config/backend transport | partial gap |
| Runtime usage | real execution path available | yes | no major gap |

## Already Present

These pieces already exist and should not be treated as missing:

- backend package:
  [ael/instruments/backends/esp32_jtag](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/backends/esp32_jtag)
- action execution for:
  - `flash`
  - `reset`
  - `gpio_measure`
- placeholder debug actions:
  - `debug_halt`
  - `debug_read_memory`
- generic native metadata/status/doctor/action entry:
  [ael/instruments/control_instrument_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/control_instrument_native_api.py)

## Missing Or Underdefined

These are the actual missing or underdefined pieces:

### 1. First-Class Instrument Identity

Current state:

- `device_type = control_instrument`

Target state:

- `device_type = multi_capability_instrument`
- `instrument_family = esp32jtag`

### 2. Capability-Family Ownership

Current state:

- observe/capture capability appears in generic native API
- debug/program actions appear in backend package

Target state:

- one instrument object explicitly owns:
  - `debug_remote`
  - `capture_control`
  - `reset_control`

### 3. Status/Doctor Semantics

Current state:

- status is generic
- doctor is essentially a wrapped preflight result

Target state:

- explicit status domains for:
  - debug endpoint
  - control/capture endpoint
  - network reachability
  - optional target enumeration health

### 4. Transport Surface

Current state:

- multiple endpoints exist, but mostly as implementation detail

Target state:

- explicit transport declaration in instrument metadata

## Not Actually Missing

These should not be treated as required gaps:

- a new backend package for action execution
- a new transport implementation for the debug path
- immediate runtime migration away from existing backend execution

## Priority

Priority order should be:

1. identity and metadata clarity
2. status/doctor object model
3. capability-family declaration
4. only then any runtime/native-surface migration

## Conclusion

The correct next design step is not "rewrite ESP32JTAG backend".

The correct next step is:

- define a first-class instrument-level API model for `ESP32JTAG`
- keep the current backend execution path intact
