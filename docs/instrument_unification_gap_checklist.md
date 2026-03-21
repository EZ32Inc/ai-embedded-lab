# Instrument Unification Gap Checklist

Status legend:

- `OK`: contract is aligned with instrument model v1 for the checked area
- `PARTIAL`: usable, but still leaks legacy or has semantic mismatch
- `BROKEN`: not aligned enough to rely on the model

## ST-Link

- `identify`: OK
  - family and backend role are exposed consistently; legacy backend is explicitly marked
- `get_capabilities`: OK
  - taxonomy enforcement is live; capability keys pass `enforce_capability_taxonomy`
- `get_status`: OK
  - taxonomy-enforced health domains; health_domain keys align with `STATUS_HEALTH_DOMAIN_KEYS`
- `doctor`: OK
  - taxonomy-enforced checks; check keys align with `DOCTOR_CHECK_KEYS`
- `preflight_probe`: OK
  - wrapped through _preflight_probe() with wrap_legacy_action; emits model-v1 ok/outcome/result/error envelope
- `program_firmware`: OK
  - unified envelope is live in interface layer and backed by controller facade
- `capture_signature`: OK
  - standardized unsupported envelope is emitted with fallback guidance
- naming consistency: OK
  - public and runtime naming is clean; legacy backend module `control_instrument_native_api.py` deleted; `stlink_native_api.py` deleted and inlined into `stlink.py`
- error consistency: OK
  - `ERROR_BOUNDARY_KEYS` and `ERROR_CODE_KEYS` enforced in `action_failure()`; `doctor_failed` and `preflight_failed` replace family-specific codes

## ESP32 JTAG

- `identify`: OK
  - family, interface, and controller metadata are stable on active paths
- `get_capabilities`: OK
  - taxonomy enforcement is live; capability keys pass `enforce_capability_taxonomy`
- `get_status`: OK
  - taxonomy-enforced health domains; capture and logic_analyzer replace old subsystem names
- `doctor`: OK
  - taxonomy-enforced checks; capture_control and logic_analyzer replace old subsystem names
- `preflight_probe`: OK
  - wrapped through _preflight_probe() with wrap_legacy_action; emits model-v1 envelope with targets/monitor_ok/logic_analyzer_ok
- `program_firmware`: OK
  - unified envelope is live in interface layer and backed by controller facade
- `capture_signature`: OK
  - unified envelope is live; compat aliases (edges/high/low) removed; only canonical names (edge_count/high_count/low_count) emitted
- naming consistency: OK
  - public and runtime naming is clean; `jtag_native_api.py` deleted and inlined into `esp32jtag.py`
- error consistency: OK
  - canonical codes enforced; `doctor_failed` and `preflight_failed` replace `jtag_*` family-specific names

## ESP32 Meter

- `identify`: OK
  - interface and provider routing is aligned with the shared model
- `get_capabilities`: OK
  - taxonomy enforcement is live; capability keys pass `enforce_capability_taxonomy`
- `get_status`: OK
  - taxonomy-enforced health domains; all keys in `STATUS_HEALTH_DOMAIN_KEYS`
- `doctor`: OK
  - taxonomy-enforced checks; meter_service and stimulation_surface added to `DOCTOR_CHECK_KEYS`
- `measure_digital`: OK
  - unified action envelope is live with compatibility aliases retained
- `measure_voltage`: OK
  - unified action envelope is live with compatibility aliases retained
- `stim_digital`: OK
  - unified action envelope is live with compatibility aliases retained
- naming consistency: OK
  - public and runtime naming is clean; `meter_native_api.py` deleted and inlined into `esp32_meter.py`
- error consistency: OK
  - boundaries renamed to canonical names (`probe_health`, `measurement`, `stimulus`); `_execute_action` fallback uses `action_failed`; `meter_*` codes replaced with canonical equivalents

## USB UART Bridge

- `identify`: OK
  - interface and provider routing is aligned with the shared model
- `get_capabilities`: OK
  - taxonomy enforcement is live; capability keys pass `enforce_capability_taxonomy`
- `get_status`: OK
  - taxonomy-enforced health domains; bridge_service key aligned to `STATUS_HEALTH_DOMAIN_KEYS`
- `doctor`: OK
  - taxonomy-enforced checks; invalid "doctor" key removed; data folded into bridge_service evidence
- `open`: OK
  - unified action envelope is live with compatibility aliases retained
- `close`: OK
  - unified action envelope is live with compatibility aliases retained
- `write_uart`: OK
  - unified action envelope is live with compatibility aliases retained
- `read_uart`: OK
  - unified action envelope is live with compatibility aliases retained
- naming consistency: OK
  - public and runtime naming is clean; internal daemon and backend naming is below the interface layer and not part of the runtime seam
- error consistency: OK
  - boundaries renamed to canonical names (`probe_health`, `uart_session`, `uart_io`); `usb_uart_*` codes replaced with canonical equivalents (`endpoint_missing`, `transport_unreachable`, `transport_error`, `action_failed`, `doctor_failed`)

## Cross-Cutting Summary

- unified provider spine: OK
- unified dispatch routing: OK
- unified action envelope: OK
  - all actions (including preflight_probe) go through wrap_legacy_action / model-v1 envelope
  - InstrumentProvider.invoke_action emits a WARNING log if a handler returns non-model-v1 shape
- stable capability taxonomy: OK
  - all four families pass `enforce_capability_taxonomy`
- normalized doctor and status semantics: OK
  - all four families emit taxonomy-enforced health domains and check keys
  - `normalize_status_result` and `normalize_doctor_result` enforce this at the interface layer
- reporting vocabulary: OK
- fallback and degradation model: OK
  - `bench_regression.py` provides FAILURE_BOUNDARY_POLICY action table and recurring run governance
- error code and boundary taxonomy: OK
  - `ERROR_BOUNDARY_KEYS` and `ERROR_CODE_KEYS` in `model.py`; `enforce_error_boundary()` and `enforce_error_code()` called from `action_failure()`; all four families emit only canonical codes and boundaries; `bench_regression.FAILURE_BOUNDARY_POLICY` updated with `measurement` and `stimulus` entries
- public controller and instrument naming: OK
- legacy backend isolation: OK
  - `controller_backend.py` now imports `flash_bmda_gdbmi` and `observe_gpio_pin` directly; all `*_native_api.py` modules deleted; content inlined into their respective interface files (`stlink.py`, `esp32jtag.py`, `esp32_meter.py`)
  - compat field aliases (edges/high/low) removed from capture_signature success_mapper; only canonical names (edge_count/high_count/low_count) are emitted; adapter_registry fallback cleaned up
