## Default Verification Schema Summary Closeout

Date: 2026-03-19

Scope:
- Add suite-level schema advisory summary to `default_verification`
- Extend structured meter-banner coverage with corrected `i2c` covers vocabulary
- Validate a second banner-style meter path through live `verify-default single_run`

Code and plan scope:
- `ael/default_verification.py`
- `ael/test_plan_schema.py`
- `tools/audit_test_plan_schema.py`
- `tests/plans/esp32c6_i2c_banner.json`
- `tests/plans/esp32c6_spi_banner.json`

What changed:
- `KNOWN_COVERS` now includes `i2c`
- `tests/plans/esp32c6_i2c_banner.json` now declares `covers: ["i2c", "voltage"]`
- `default_verification` now emits suite-level `schema_advisory_summary` with:
  - `structured_step_count`
  - `legacy_step_count`
  - `test_kind_counts`
  - `supported_instrument_status_counts`
  - `warning_messages`
  - `instrument_specific_steps`
- worker-summary stdout now includes schema rollups:
  - `schema structured=... legacy=...`
  - `schema_test_kinds ...`
  - `schema_instrument_support ...`
- `audit-test-schema` now surfaces `labels` and `covers` in its report contract and text output

Static regression evidence:
- `PYTHONPATH=. pytest -q tests/test_default_verification.py tests/test_test_plan_schema.py tests/test_plan_schema_repo.py tests/test_inventory.py tests/test_stage_explain.py tests/test_audit_test_plan_schema.py`
- Result: `96 passed in 3.48s`

Representative live validation:
- config: `/tmp/default_verification_meter_spi_banner_single.json`
- board: `esp32c6_devkit`
- test: `tests/plans/esp32c6_spi_banner.json`
- PASS run id: `2026-03-19_21-57-16_esp32c6_devkit_esp32c6_spi_banner`

Live validation outcome:
- `verify-default single_run` passed through `plan, run, check, report`
- key checks passed:
  - `uart.verify`
  - `instrument.signature`
- final payload included both step-level and suite-level schema summary:
  - `plan_schema_kind: structured`
  - `test_kind: instrument_specific`
  - `supported_instrument_advisory.status: declared_supported`
  - `schema_advisory_summary.supported_instrument_status_counts.declared_supported = 1`

Why this matters:
- Advisory data is now visible at the level operators actually read after a suite run, not just in per-step result payloads.
- The second banner-style live validation reduces the chance that the earlier `uart_banner` success was only a single-plan special case.
- `i2c` is now a first-class controlled cover term instead of being forced into a vague `voltage` bucket.

Conclusion:
- The schema/advisory contract now has better semantic coverage and a more useful runtime summary surface.
- Meter banner paths continue to pass real `verify-default` validation while carrying structured schema metadata end-to-end.
