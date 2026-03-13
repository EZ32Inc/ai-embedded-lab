# Default Verification

Run the current baseline sequence with:

```bash
python3 -m ael verify-default run
```

Stress it with:

```bash
python3 -m ael verify-default repeat --limit 20
```

Health-hardening note:

- repeat-mode health output is intended to show bounded repeatability evidence
- current health summaries expose:
  - total pass/fail counts
  - degraded instrument counts
  - failure-category counts when failures occur
  - expected Local Instrument Interface path counts:
    - `control_instrument_native_api`
    - `meter_native_api`

Preferred repeated-run mode:

- use `verify-default repeat --limit N` for repeated baseline checks
- this repeats independently per worker
- do not use a shell loop around `verify-default run` when you want each board to
  keep progressing on its own
- when a user asks to run default verification `N` times, interpret that request
  as `verify-default repeat --limit N` unless they explicitly ask for
  suite-round serialization

Current execution model:

- default verification selects DUT tests from inventory; it does not define
  separate test identities or duplicate setup
- the DUT test plan remains the single source of truth for setup and expected
  checks
- the current default execution policy is `serial`
- the current configured baseline has one DUT test
- `verify-default repeat` still repeats independently per worker when the suite
  has more than one configured task
- `verify-default repeat-until-fail` remains supported as a compatibility alias
  for the same behavior
- when a worker fails because an external instrument is unstable, unrelated
  workers should keep progressing and the failure summary should classify the
  degraded instrument condition explicitly
- default verification currently retries transient instrument transport/API
  failures once, but fails fast for clearly unreachable instruments and does
  not auto-retry verify-stage instrument mismatches

Current default sequence:

1. `stm32f103_gpio_signature`
   - board: `stm32f103`
   - test: `tests/plans/stm32f103_gpio_signature.json`
   - evidence: logic-analyzer `gpio.signal`

Current validated baseline:

- default verification passed on the current single configured DUT test
- latest validated default-verification run:
  - `2026-03-13_18-22-08_stm32f103_stm32f103_gpio_signature`

Known-good comparison artifact:

- STM32F103:
  - `runs/2026-03-13_18-22-08_stm32f103_stm32f103_gpio_signature/artifacts/evidence.json`

Legacy note:

- old raw probe configs such as `configs/esp32jtag.yaml` are still accepted as legacy control-instrument config forms
- they now warn: `Using legacy shared probe config; explicit instrument instance is recommended.`
