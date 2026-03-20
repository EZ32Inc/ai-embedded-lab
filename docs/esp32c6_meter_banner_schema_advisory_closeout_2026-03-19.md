## ESP32-C6 Meter Banner Schema Advisory Closeout

Date: 2026-03-19

Scope:
- Structured schema formalization for ESP32-C6 banner-style meter plans
- `default_verification` warning-only schema advisory surfacing
- Representative live validation for a banner-style meter path

Plans formalized in this round:
- `tests/plans/esp32c6_spi_banner.json`
- `tests/plans/esp32c6_uart_banner.json`
- `tests/plans/esp32c6_i2c_banner.json`

Code and test scope:
- `ael/default_verification.py`
- `tests/test_default_verification.py`
- `tests/test_audit_test_plan_schema.py`

What changed:
- Banner-style ESP32-C6 meter plans now declare structured metadata:
  - `schema_version: "1.0"`
  - `test_kind: "instrument_specific"`
  - `supported_instruments: ["esp32_meter"]`
  - `requires: {"mailbox": false, "datacapture": true}`
- `default_verification` now carries warning-only schema advisory data into single-run results:
  - `plan_schema_kind`
  - `schema_version`
  - `test_kind`
  - `supported_instruments`
  - `supported_instrument_advisory`
  - `schema_advisories`
  - `schema_warning_messages`

Static regression evidence:
- `PYTHONPATH=. pytest -q tests/test_default_verification.py tests/test_test_plan_schema.py tests/test_plan_schema_repo.py tests/test_inventory.py tests/test_stage_explain.py tests/test_audit_test_plan_schema.py`
- Result: `93 passed in 3.39s`

Representative live validation:
- config: `/tmp/default_verification_meter_banner_single.json`
- board: `esp32c6_devkit`
- test: `tests/plans/esp32c6_uart_banner.json`
- PASS run id: `2026-03-19_21-50-29_esp32c6_devkit_esp32c6_uart_banner`

Live validation outcome:
- `verify-default single_run` completed successfully through `plan, run, check, report`
- key checks passed:
  - `uart.verify`
  - `instrument.signature`
- result payload preserved schema advisory fields during real execution:
  - `plan_schema_kind: structured`
  - `test_kind: instrument_specific`
  - `supported_instrument_advisory.status: declared_supported`
  - `schema_advisories` included the expected instrument-path explanation and support summary

Why this matters:
- This round proves the warning-only schema advisory surface is not limited to inventory/explain output.
- The same advisory contract now survives the real `default_verification` entrypoint for a banner-style meter path.
- The result is stronger than a pure unit test because it confirms the runtime summary still carries the schema information after a full build, flash, run, and check cycle.

Conclusion:
- Structured `instrument_specific` coverage now includes meter banner paths, not just GPIO/ADC/selftest variants.
- `default_verification` can surface schema guidance without changing runner dispatch semantics.
- `verify-default single_run` remains the lowest-blast-radius way to validate new schema-backed verification paths before broader suite rollout.
