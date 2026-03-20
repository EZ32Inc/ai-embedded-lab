# Instrument Unification Gap Checklist

Status legend:

- `OK`: contract is aligned with instrument model v1 for the checked area
- `PARTIAL`: usable, but still leaks legacy or has semantic mismatch
- `BROKEN`: not aligned enough to rely on the model

## ST-Link

- `identify`: OK
  - family and backend role are exposed consistently; legacy backend is explicitly marked
- `get_capabilities`: PARTIAL
  - capability keys are exposed, but taxonomy enforcement is still soft
- `get_status`: PARTIAL
  - normalized top-level envelope exists; health domains still need stricter shared taxonomy
- `doctor`: PARTIAL
  - normalized health, failure boundary, and recovery hint are present; check bodies still vary by family
- `preflight_probe`: PARTIAL
  - action is usable and routable, but response details remain backend-shaped
- `program_firmware`: OK
  - unified envelope is live in interface layer and backed by controller facade
- `capture_signature`: OK
  - standardized unsupported envelope is emitted with fallback guidance
- naming consistency: PARTIAL
  - public and runtime naming is clean; legacy backend module names still exist internally
- error consistency: PARTIAL
  - error envelope is unified, but boundary taxonomy is not fully enforced everywhere

## ESP32 JTAG

- `identify`: OK
  - family, interface, and controller metadata are stable on active paths
- `get_capabilities`: PARTIAL
  - capability keys are exposed, but family-local detail still leaks under result payloads
- `get_status`: PARTIAL
  - normalized top-level envelope exists; health domains still need stricter shared taxonomy
- `doctor`: PARTIAL
  - normalized health, failure boundary, and recovery hint are present; checks are not yet fully canonicalized
- `preflight_probe`: PARTIAL
  - action is useful and provider-routed, but detailed payload shape remains legacy-heavy
- `program_firmware`: OK
  - unified envelope is live in interface layer and backed by controller facade
- `capture_signature`: PARTIAL
  - unified envelope is live, but compatibility aliases are still required by downstream consumers
- naming consistency: PARTIAL
  - public and runtime naming is clean; `jtag_native_api.py` remains a family backend detail
- error consistency: PARTIAL
  - envelope is shared, but no full family-independent error code set exists yet

## ESP32 Meter

- `identify`: OK
  - interface and provider routing is aligned with the shared model
- `get_capabilities`: PARTIAL
  - taxonomy keys are exposed, but some result details still use meter-specific naming
- `get_status`: PARTIAL
  - normalized top-level envelope exists; health semantics still need stronger cross-family alignment
- `doctor`: PARTIAL
  - normalized health and recovery fields are present; detailed checks remain family-shaped
- `measure_digital`: OK
  - unified action envelope is live with compatibility aliases retained
- `measure_voltage`: OK
  - unified action envelope is live with compatibility aliases retained
- `stim_digital`: OK
  - unified action envelope is live with compatibility aliases retained
- naming consistency: PARTIAL
  - public and runtime naming is clean; `meter_native_api.py` remains an internal backend module
- error consistency: PARTIAL
  - result and error envelope is shared, but taxonomy-backed boundaries are not fully enforced

## USB UART Bridge

- `identify`: OK
  - interface and provider routing is aligned with the shared model
- `get_capabilities`: PARTIAL
  - stable top-level keys exist, but capability taxonomy is still soft-enforced
- `get_status`: PARTIAL
  - normalized top-level envelope exists; health domains remain simpler than other families
- `doctor`: PARTIAL
  - normalized health and recovery fields are present; detailed checks remain bridge-specific
- `open`: OK
  - unified action envelope is live with compatibility aliases retained
- `close`: OK
  - unified action envelope is live with compatibility aliases retained
- `write_uart`: OK
  - unified action envelope is live with compatibility aliases retained
- `read_uart`: OK
  - unified action envelope is live with compatibility aliases retained
- naming consistency: PARTIAL
  - public and runtime naming is clean; internal daemon and backend naming still exists below the interface layer
- error consistency: PARTIAL
  - result and error envelope is shared, but shared boundary taxonomy is not fully enforced

## Cross-Cutting Summary

- unified provider spine: OK
- unified dispatch routing: OK
- unified action envelope: PARTIAL
- stable capability taxonomy: PARTIAL
- normalized doctor and status semantics: PARTIAL
- reporting vocabulary: OK
- fallback and degradation model: PARTIAL
- public controller and instrument naming: OK
- legacy backend isolation: PARTIAL
