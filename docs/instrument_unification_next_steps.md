# Instrument Unification Next Steps

## Phase 1

Goal:

- finish the first working semantic slice around the new action envelope

Concrete tasks:

- migrate `capture_signature` to the model v1 envelope
- migrate `measure_digital` and `measure_voltage` to the model v1 envelope
- add shared boundary codes for `interface_contract`, `firmware_programming`, `capture`, `transport`, `service`
- change adapter callers to read `ok/outcome/result/error` first, with legacy fallback second

Risk:

- medium
- envelope shims can drift if old and new fields are both written but not kept consistent

## Phase 2

Goal:

- normalize semantics for capability, doctor, and status

Concrete tasks:

- convert capability declarations to the stable taxonomy in `instrument_model_v1.md`
- normalize doctor outputs to a stable `checks` schema
- normalize status outputs to a stable `health_domains` taxonomy
- define shared degradation/fallback strategies by failure boundary

Risk:

- medium to high
- doctor/status changes touch diagnostics, triage, and user-facing interpretation

## Phase 3

Goal:

- retire legacy naming from higher layers and reduce native-api leakage to backend-only detail

Concrete tasks:

- remove remaining `*_native_api` naming from reporting and summaries
- move legacy wrappers behind interface adapters only
- reduce direct imports of old native API modules from higher-level code
- add migration assertions so new providers must emit model-v1 envelopes

Risk:

- medium
- cleanup can expose callers that were implicitly relying on legacy shape or names

## Test Matrix

| Action | stlink | esp32jtag | esp32_meter | usb_uart_bridge |
| --- | --- | --- | --- | --- |
| `identify` | x | x | x | x |
| `get_capabilities` | x | x | x | x |
| `get_status` | x | x | x | x |
| `doctor` | x | x | x | x |
| `preflight_probe` | x | x | - | - |
| `program_firmware` | x | x | - | - |
| `capture_signature` | - | x | - | - |
| `measure_digital` | - | - | x | - |
| `measure_voltage` | - | - | x | - |
| `stim_digital` | - | - | x | - |
| `open` | - | - | - | x |
| `close` | - | - | - | x |
| `write_uart` | - | - | - | x |
| `read_uart` | - | - | - | x |

## Migration Strategy

Safe rollout plan:

1. introduce model-v1 envelope in interface layer only
2. keep legacy `status/data/error` aliases until all adapter callers are migrated
3. migrate one action family-by-family with explicit tests
4. switch reports and summaries after caller compatibility is in place
5. remove legacy aliases only after end-to-end validation proves no caller still depends on them

Backward compatibility:

- short term: dual-shape responses are allowed
- medium term: callers must prefer `ok/outcome/result/error`
- long term: `status/data/error` should become compatibility shims only at the outer boundary, then be removed
