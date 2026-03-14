# Default Verification

Run the current baseline sequence with:

```bash
python3 -m ael verify-default run
```

Stress it with:

```bash
python3 -m ael verify-default repeat --limit 20
```

For real bench execution, prefer:

```bash
tools/run_live_bench.sh python3 -m ael verify-default run
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

Live-bench validity:

- `verify-default` is a live-bench command when it is intended to touch real
  DUTs and instruments
- do not do a sandbox trial run first for such commands
- if a run is blocked by sandbox/network policy before reaching the bench,
  classify it as `INVALID`, not `FAIL`
- `INVALID` runs must not be counted as DUT, probe, instrument, or suite
  failures

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
- the current configured baseline has five DUT tests
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
- summaries and operator interpretation should distinguish:
  - `PASS`: real bench reached and validation passed
  - `FAIL`: real bench reached and validation failed
  - `INVALID`: real bench not reached

Current default sequence:

1. `esp32c6_gpio_signature_with_meter`
   - board: `esp32c6_devkit`
   - test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
   - evidence: `uart.verify`, `instrument.signature`
2. `rp2040_gpio_signature`
   - board: `rp2040_pico`
   - test: `tests/plans/rp2040_gpio_signature.json`
   - evidence: logic-analyzer `gpio.signal`
3. `stm32f103_gpio_signature`
   - board: `stm32f103_gpio`
   - test: `tests/plans/stm32f103_gpio_signature.json`
   - evidence: logic-analyzer `gpio.signal`
4. `stm32f103_uart_banner`
   - board: `stm32f103_uart`
   - test: `tests/plans/stm32f103_uart_banner.json`
   - evidence: `uart.verify`, `gpio.signal`
5. `stm32f411_gpio_signature`
   - board: `stm32f411ceu6`
   - test: `tests/plans/stm32f411_gpio_signature.json`
   - evidence: logic-analyzer `gpio.signal`

Current validated baseline:

- the configured baseline now has five DUT tests, including `stm32f411_gpio_signature`
- latest live default-verification run with the five-step configuration:
  - `2026-03-14_09-27-35_rp2040_pico_rp2040_gpio_signature` -> `PASS`
  - `2026-03-14_09-27-58_stm32f103_gpio_stm32f103_gpio_signature` -> `PASS`
  - `2026-03-14_09-28-28_stm32f103_uart_stm32f103_uart_banner` -> `PASS`
  - `2026-03-14_09-29-06_stm32f411ceu6_stm32f411_gpio_signature` -> `PASS`
- suite nuance:
  - the same run reported `esp32c6_gpio_signature_with_meter` as `FAIL` at `flash` because no serial port was found
  - that is an existing ESP32-C6 bench availability issue, not an F411 regression

Known-good comparison artifact:

- ESP32-C6:
  - `runs/2026-03-13_19-17-59_esp32c6_devkit_esp32c6_gpio_signature_with_meter/artifacts/evidence.json`
- RP2040:
  - `runs/2026-03-13_19-18-52_rp2040_pico_rp2040_gpio_signature/artifacts/evidence.json`
- STM32F103 GPIO DUT:
  - `runs/2026-03-13_19-19-14_stm32f103_gpio_stm32f103_gpio_signature/artifacts/evidence.json`
- STM32F103 UART DUT:
  - `runs/2026-03-13_19-19-40_stm32f103_uart_stm32f103_uart_banner/artifacts/evidence.json`
- STM32F411:
  - `runs/2026-03-14_09-29-06_stm32f411ceu6_stm32f411_gpio_signature/artifacts/evidence.json`

Legacy note:

- old raw probe configs such as `configs/esp32jtag.yaml` are still accepted as legacy control-instrument config forms
- they now warn: `Using legacy shared probe config; explicit instrument instance is recommended.`
