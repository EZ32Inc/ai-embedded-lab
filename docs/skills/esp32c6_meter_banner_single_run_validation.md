# ESP32-C6 Meter Banner Single-Run Validation

Use this when a newly formalized ESP32-C6 meter-backed banner plan needs a real `verify-default` check without running the full baseline.

## Purpose

- Validate that a banner-style `instrument_specific` plan still works through the actual `default_verification` entrypoint.
- Confirm warning-only schema advisory data is preserved in the final result payload.
- Keep blast radius low by exercising one board, one test, one instrument path.

## Recommended representative path

- Board: `esp32c6_devkit`
- Test: `tests/plans/esp32c6_uart_banner.json`
- Instrument: `esp32s3_dev_c_meter`

This path is a good representative because it exercises both UART observation and meter-backed instrument checks while staying close to the established ESP32-C6 meter bench setup.

## Single-run config

Write a temporary config like this:

```json
{
  "mode": "sequence",
  "continue_on_failure": false,
  "steps": [
    {
      "board": "esp32c6_devkit",
      "test": "tests/plans/esp32c6_uart_banner.json"
    }
  ]
}
```

Notes:
- Do not add `name` inside the step. The CLI rejects that as a redefinition of DUT identity/setup fields.
- Keep the config in `/tmp` so the run is disposable.

## Command

```bash
PYTHONPATH=. python3 -m ael verify-default run --file /tmp/default_verification_meter_banner_single.json
```

## What success looks like

- stdout shows `PASS: Run verified`
- summary includes:
  - `key_checks_passed=uart.verify, instrument.signature`
  - `instrument=esp32s3_dev_c_meter`
- final JSON payload includes:
  - `plan_schema_kind: structured`
  - `test_kind: instrument_specific`
  - `supported_instrument_advisory.status: declared_supported`
  - `schema_advisories` mentioning instrument-side measurement and declared support

## What to check if it fails

- Config shape error before execution:
  - remove unsupported fields such as `name` from the step payload
- Flash/load failure:
  - inspect `runs/<run_id>/result.json` and `runs/<run_id>/flash.log` together
- Bench/runtime failure after load:
  - inspect `artifacts/verify_result.json` and `artifacts/evidence.json`
- Wrong advisory status:
  - confirm `supported_instruments` in the plan and instrument instance type in `configs/instrument_instances/<id>.yaml`

## Reusable takeaway

- For new structured meter plans, validate one representative banner path first.
- Treat `verify-default single_run` as the contract check for whether schema-backed advisory data survives the real execution entrypoint.
