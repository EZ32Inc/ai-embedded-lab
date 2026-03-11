# Default Verification

Run the current baseline sequence with:

```bash
python3 -m ael verify-default run
```

Stress it with:

```bash
python3 -m ael verify-default repeat --limit 20
```

Preferred repeated-run mode:

- use `verify-default repeat --limit N` for repeated baseline checks
- this repeats independently per worker
- do not use a shell loop around `verify-default run` when you want each board to
  keep progressing on its own
- when a user asks to run default verification `N` times, interpret that request
  as `verify-default repeat --limit N` unless they explicitly ask for
  suite-round serialization

Current execution model:

- the default verification baseline is treated as a suite of independent board
  verification workers
- the current default execution policy is `parallel`
- `verify-default run` starts all three workers immediately
- `verify-default repeat` repeats independently per worker rather than waiting
  for synchronized suite rounds
- `verify-default repeat-until-fail` remains supported as a compatibility alias
  for the same behavior
- when a worker fails because an external instrument is unstable, unrelated
  workers should keep progressing and the failure summary should classify the
  degraded instrument condition explicitly
- default verification currently retries transient instrument transport/API
  failures once, but fails fast for clearly unreachable instruments and does
  not auto-retry verify-stage instrument mismatches

Current default sequence:

1. `esp32c6_golden_gpio`
   - board: `esp32c6_devkit`
   - test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
   - evidence: UART + meter-backed `instrument.signature`
2. `rp2040_golden_gpio_signature`
   - board: `rp2040_pico`
   - test: `tests/plans/gpio_signature.json`
   - control instrument instance: `esp32jtag_rp2040_lab`
   - evidence: logic-analyzer `gpio.signal`
3. `stm32f103_golden_gpio_signature`
   - board: `stm32f103`
   - test: `tests/plans/gpio_signature.json`
   - control instrument instance: `esp32jtag_stm32_golden`
   - evidence: logic-analyzer `gpio.signal`

Current validated baseline:

- default verification passed `10/10`
- STM32F401 golden GPIO passed `10/10`
- STM32F103 golden GPIO passed `10/10`
- STM32F401 direct post-flash `+5s` stability benchmark passed `20/20`

Known-good comparison artifacts:

- ESP32-C6:
  - `runs/2026-03-09_14-57-25_esp32c6_devkit_esp32c6_gpio_signature_with_meter/artifacts/evidence.json`
- RP2040:
  - `runs/2026-03-09_14-58-12_rp2040_pico_gpio_signature/artifacts/evidence.json`
- STM32F103:
  - `runs/2026-03-09_14-58-42_stm32f103_gpio_signature/artifacts/evidence.json`

Legacy note:

- old raw probe configs such as `configs/esp32jtag.yaml` are still accepted as legacy control-instrument config forms
- they now warn: `Using legacy shared probe config; explicit instrument instance is recommended.`
