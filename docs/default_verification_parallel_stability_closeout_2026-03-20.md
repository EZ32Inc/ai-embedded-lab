# Default Verification Parallel Stability Closeout 2026-03-20

## Scope

This closeout records the live stabilization of parallel `default verification`
after the schema/default-verification changes and the ST-Link recovery work
landed.

The question for this closeout was narrow:

- can the six-test default baseline run in parallel repeatedly
- does the previously unstable ST-Link path now hold inside that parallel batch
- do the schema/execution changes now have real bench evidence behind them

## What Failed Earlier

The blocking instability was not the RP2040 or STM32G431 GPIO-signature tests.
Those failures were transient ESP32 JTAG setup health issues and later recovered.

The durable blocker was `stm32f103_gpio_no_external_capture_stlink`.

Earlier failure signatures showed two layers of problems:

- `st-util` single-session limitations during repeated local use
- direct ST-Link attach failures below GDB, including:
  - `Found 0 stlink programmers`
  - `Failed to enter SWD mode`
  - `GET_VERSION send request failed: LIBUSB_ERROR_TIMEOUT`
  - `ENTER_SWD send request failed: LIBUSB_ERROR_TIMEOUT`

This separated the real issue from the false lead that "parallel default
verification itself is the root cause". Parallel execution exposed the problem,
but the unstable boundary was the ST-Link attach path.

## Changes That Mattered

Relevant implementation changes:

- [ael/adapters/flash_bmda_gdbmi.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/flash_bmda_gdbmi.py)
  - run local `st-util` with `--multi`
  - add a direct `st-info --probe` health gate before GDB-server startup
  - classify direct-probe failures as `usb_missing`, `swd_attach_failed`, or
    `probe_timeout`
  - retry those direct-probe failures with bounded backoff before startup
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
  - add grouped execution support for `mode: sequence`
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
  - restore the current default baseline to one parallel batch containing all
    six experiments

Supporting tests passed during the work:

- `PYTHONPATH=. pytest -q tests/test_flash_bmda_gdbmi.py`
- `PYTHONPATH=. pytest -q tests/test_default_verification.py`

## Live Validation Evidence

Single-test recovery and repetition evidence:

- ST-Link pass after direct-probe recovery:
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-29-16_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- back-to-back ST-Link passes:
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-30-41_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-31-03_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

First full six-way parallel pass:

- [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
- [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_rp2040_pico_rp2040_gpio_signature/result.json)
- [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32f411ceu6_stm32f411_gpio_signature/result.json)
- [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32g431cbu6_stm32g431_gpio_signature/result.json)
- [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32h750vbt6_stm32h750_wiring_verify/result.json)
- [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

Three consecutive six-way parallel passes:

- run set `2026-03-20_10-36-49`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- run set `2026-03-20_10-37-43`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- run set `2026-03-20_10-38-37`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

## Conclusion

The current claim is now supported by live evidence:

- the six-test default baseline can run in parallel
- the repaired ST-Link path now survives repeated participation in that parallel
  baseline
- the schema/default-verification execution changes are standing on repeatable
  bench evidence, not just unit tests or a single lucky run

Within the scope of this closeout, the baseline should be treated as stable.

## Why Closeout Was Required Here

The risk here was stopping too early after the code fix and one green run.

That would have missed the actual delivery requirement:

- identify the real failure boundary
- prove the repaired path under repetition
- capture the debug method for reuse

This closeout exists to prevent "commit done" from being mistaken for "pattern
validated".


## Post-Closeout Follow-Up: ESP32 JTAG Probe-Config Regression

Later on `2026-03-20`, a new `default verification` run failed with `1/6 PASS`
and `5/6 FAIL`, including all four `ESP32JTAG`-backed tests.

That run initially looked like another bench-health incident, but the boundary
was different:

- `instrument doctor` on `esp32jtag_rp2040_lab` at `192.168.2.63` was healthy
- live `ping`, `TCP 4242`, `monitor targets`, and LA self-test were all OK
- the failing `ael run` path still died immediately in `preflight`

The decisive comparison was between the failing run's effective config and its
materialized run plan:

- [failing rp2040 run_plan.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_12-47-14_rp2040_pico_rp2040_gpio_signature/artifacts/run_plan.json)
- [failing rp2040 config_effective.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_12-47-14_rp2040_pico_rp2040_gpio_signature/config_effective.json)

The run plan `probe_cfg` had lost the metadata needed by the new provider
registry to recognize the control instrument family. In particular,
`instance_id`, `type_id`, `communication`, and `capability_surfaces` were not
being preserved by `normalize_probe_cfg()`.

That meant the failure boundary was not network reachability. It was a
run-time config-shape regression introduced after the instrument-interface
standardization work.

### Repair

The recovery changes were:

- [ael/strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
  - preserve `instance`, `type`, `communication`, and
    `capability_surfaces` when building normalized `probe_cfg`
- [ael/instruments/interfaces/registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/registry.py)
  - add a compatibility fallback so legacy/minimal ESP32 JTAG probe shapes are
    still recognized as `esp32jtag`

Regression tests added:

- [tests/test_strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_strategy_resolver.py)
- [tests/test_instrument_interface_registry.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_instrument_interface_registry.py)

### Recovery Evidence

Recovered single-test runs:

- [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-08-08_rp2040_pico_rp2040_gpio_signature/result.json)
- [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-03_stm32f411ceu6_stm32f411_gpio_signature/result.json)
- [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-08_stm32g431cbu6_stm32g431_gpio_signature/result.json)
- [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-22_stm32h750vbt6_stm32h750_wiring_verify/result.json)

Recovered full baseline pass:

- [default verification run set `2026-03-20_13-10-38`](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-10-38_rp2040_pico_rp2040_gpio_signature/result.json)

The follow-up matters because it validates a stronger claim than the original
closeout alone:

- the parallel baseline remained stable through a later refactor-induced
  regression
- the regression was diagnosed by comparing doctor-path config shape against
  run-path config shape
- the repaired system returned to `6/6 PASS` without changing the actual bench
  setups
