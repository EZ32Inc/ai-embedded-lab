# Instrument Unification Next Steps

Current Status:

- provider and registry spine is active
- semantic model v1 is live across the main families for metadata, health, and the first set of real actions
- active runtime surfaces now largely use `controller`, `instrument_interface`, and `instrument_family` vocabulary
- the remaining work is mostly legacy-seam retirement and stronger taxonomy enforcement, not first-pass architecture design

## Phase 1

Goal:

- complete the first migration slice for the shared action envelope

Concrete tasks:

- keep `program_firmware`, `capture_signature`, meter actions, and UART bridge actions on the model v1 envelope
- migrate remaining consumers to read `ok`, `outcome`, `result`, and `error` first, with legacy fallback second
- add regression tests that detect divergence between new and compatibility fields

Risk:

- medium
- dual-shape responses can drift if compatibility aliases are not kept consistent with the canonical envelope

## Phase 2

Goal:

- tighten semantics for capability, doctor, and status around the documented model

Concrete tasks:

- convert capability declarations from soft taxonomy to enforced shared keys
- normalize doctor outputs to a stable `checks` schema across all four families
- normalize status outputs to a stable shared health-domain taxonomy
- define shared degradation and fallback strategies by failure boundary

Risk:

- medium to high
- doctor and status changes touch diagnostics, triage, and user-facing interpretation

## Phase 3

Goal:

- retire legacy seams from higher layers and reduce native-api leakage to backend-only detail

Concrete tasks:

- keep public and runtime naming on `controller` and `instrument_*` vocabulary only
- reduce direct first-class status of `control_instrument_native_api.py`
- move remaining legacy wrappers behind interface adapters or controller backend facades only
- add migration assertions so new providers must emit model-v1 envelopes and taxonomy-backed capability keys
- remove compatibility fields only after live validation proves no active caller depends on them

Risk:

- medium
- cleanup can expose callers that were implicitly relying on legacy shape or legacy names

## Test Matrix

| Action | stlink | esp32jtag | esp32_meter | usb_uart_bridge |
| --- | --- | --- | --- | --- |
| `identify` | x | x | x | x |
| `get_capabilities` | x | x | x | x |
| `get_status` | x | x | x | x |
| `doctor` | x | x | x | x |
| `preflight_probe` | x | x | - | - |
| `program_firmware` | x | x | - | - |
| `capture_signature` | unsupported | x | - | - |
| `measure_digital` | - | - | x | - |
| `measure_voltage` | - | - | x | - |
| `stim_digital` | - | - | x | - |
| `open` | - | - | - | x |
| `close` | - | - | - | x |
| `write_uart` | - | - | - | x |
| `read_uart` | - | - | - | x |

## Migration Strategy

Safe rollout plan:

1. keep model-v1 envelope canonical in the interface layer
2. keep compatibility aliases until all active callers are migrated and live-validated
3. migrate one family or one action slice at a time with explicit tests
4. shift reports, summaries, CLI, and workflow payloads only after caller compatibility is in place
5. retire compatibility fields only after end-to-end validation proves no active caller still depends on them

Backward compatibility:

- short term: dual-shape responses are allowed
- medium term: callers must prefer `ok`, `outcome`, `result`, and `error`
- long term: `status`, `data`, legacy controller fields, and native-api naming should become compatibility shims only at the outer boundary, then be removed
