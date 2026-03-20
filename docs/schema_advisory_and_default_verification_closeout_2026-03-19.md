## Schema Advisory And Default Verification Closeout

Date: 2026-03-19

Scope:
- Structured test-plan schema adoption for mailbox and meter-backed paths
- Inventory / stage-explain advisory surfaces
- Default-verification representative-path validation
- ESP-IDF load adapter bug found during live validation

Code and plan scope:
- Schema and advisory surfaces:
  - `ael/test_plan_schema.py`
  - `ael/inventory.py`
  - `ael/stage_explain.py`
  - `tools/audit_test_plan_schema.py`
- Runtime fix:
  - `ael/adapter_registry.py`
- New structured `instrument_specific` pilots:
  - `tests/plans/esp32c3_gpio_signature_with_meter.json`
  - `tests/plans/esp32c6_adc_meter.json`

Validation goals:
- Prove that schema metadata and advisory changes did not break the real `verify-default` entrypoint.
- Exercise one mailbox-style path and one meter-backed path through `verify-default single_run`.
- Identify whether any failure belongs to schema selection, runtime dispatch, or bench execution.

Representative live validation runs:
- Mailbox representative path:
  - config: `/tmp/default_verification_mailbox_single.json`
  - board: `stm32f103_gpio_stlink`
  - test: `tests/plans/stm32f103_gpio_no_external_capture_stlink.json`
  - PASS run id: `2026-03-19_21-32-44_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink`
- Meter representative path:
  - config: `/tmp/default_verification_meter_single.json`
  - board: `esp32c6_devkit`
  - test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
  - initial FAIL run id: `2026-03-19_21-29-20_esp32c6_devkit_esp32c6_gpio_signature_with_meter`
  - post-fix PASS run id: `2026-03-19_21-37-29_esp32c6_devkit_esp32c6_gpio_signature_with_meter`

Static regression evidence:
- `PYTHONPATH=. pytest -q tests/test_load_adapter_logging.py tests/test_test_plan_schema.py tests/test_plan_schema_repo.py tests/test_inventory.py tests/test_stage_explain.py tests/test_audit_test_plan_schema.py`
- Result after fix: `58 passed in 1.98s`

What failed first:
- The first meter `verify-default single_run` did not fail because of schema selection or bench reachability.
- Build completed.
- `flash.log` showed a successful ESP-IDF flash with verified hashes.
- The final run still failed at load/flash with:
  - `adapter execute failed: local variable 'payload' referenced before assignment`

Real root cause:
- `_LoadAdapter.execute()` in `ael/adapter_registry.py` handled `idf_esptool` differently from native-control load paths.
- The `idf_esptool` branch only stored `ok`.
- Later common-path logic still referenced `payload`.
- That turned a successful flash into an adapter exception and misclassified the run as a load-stage failure.

Why this mattered:
- Without reading `result.json` and `flash.log` together, the failure looked like a meter-path or flash instability.
- The real issue was a control-plane bug in adapter result normalization.
- This is exactly the kind of false lead that can waste time if the review stops at stdout stage labels.

Evidence that separated false leads from the real cause:
- `runs/2026-03-19_21-29-20_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json`
  - `failed_step: load`
  - `error_summary: adapter execute failed: local variable 'payload' referenced before assignment`
- `runs/2026-03-19_21-29-20_esp32c6_devkit_esp32c6_gpio_signature_with_meter/artifacts/result.json`
  - repeated load attempts, same Python exception each time
- `runs/2026-03-19_21-29-20_esp32c6_devkit_esp32c6_gpio_signature_with_meter/flash.log`
  - full flash success with `Hash of data verified`

Fix applied:
- Normalize the `idf_esptool` path in `_LoadAdapter.execute()` so it always defines a local payload for common-path handling.
- Add focused regression coverage in `tests/test_load_adapter_logging.py` for:
  - ESP-IDF flash success
  - ESP-IDF flash failure

Post-fix live result:
- Re-running the same meter `verify-default single_run` passed.
- The successful run reached real validation and reported:
  - `key_checks_passed=uart.verify, instrument.signature`
- This confirms the earlier failure was not a bench-side meter-path problem.

Outcome summary:
- Mailbox representative path: PASS
- Meter representative path: PASS after adapter fix
- Schema advisory surfaces did not break `verify-default`
- New structured `instrument_specific` pilots are compatible with the real entrypoint

Conclusion:
- The current schema-advisory expansion is validated at three levels:
  - static contract tests
  - explain / inventory surfaces
  - live `verify-default single_run` representative paths
- The only live failure found in this round was a real adapter bug, now fixed.
- `verify-default single_run` is a strong low-blast-radius validation pattern for proving whether a change broke entrypoint wiring or only exposed a deeper runtime issue.
