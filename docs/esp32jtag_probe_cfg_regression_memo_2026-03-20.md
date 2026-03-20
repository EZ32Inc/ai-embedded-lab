# ESP32 JTAG Probe-Config Regression Memo 2026-03-20

## Problem

After the instrument-interface standardization work, a later live `default
verification` run regressed from a previously stable `6/6 PASS` baseline to
`1/6 PASS`. All four `ESP32JTAG`-backed experiments failed immediately in
`preflight`.

At first glance the failures resembled setup-health problems, but direct health
checks contradicted that theory. For `esp32jtag_rp2040_lab` at `192.168.2.63`:

- ICMP reachability was good
- TCP `4242` was reachable
- `monitor targets` worked
- LA self-test worked

That meant the failure boundary was somewhere between run-plan materialization
and native provider dispatch.

## Root Cause

The new provider registry resolves control-instrument family primarily from
`type_id`, explicit family metadata, or `communication.surfaces`.

The run-time `probe_cfg` produced by
[ael/strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
was too aggressively normalized. It preserved only a minimal legacy subset and
dropped:

- `instance_id`
- `type_id`
- `communication`
- `capability_surfaces`

As a result, the provider layer could not identify the control instrument as
`esp32jtag`, and `preflight_probe` failed before any real network or JTAG
interaction began.

Evidence:

- [failing run_plan.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_12-47-14_rp2040_pico_rp2040_gpio_signature/artifacts/run_plan.json)
- [failing config_effective.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_12-47-14_rp2040_pico_rp2040_gpio_signature/config_effective.json)

## Fix

Implementation changes:

- [ael/strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
  - preserve control-provider metadata in `normalize_probe_cfg()`
- [ael/instruments/interfaces/registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/registry.py)
  - add compatibility fallback for legacy/minimal ESP32 JTAG shapes

Regression tests:

- [tests/test_strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_strategy_resolver.py)
- [tests/test_instrument_interface_registry.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_instrument_interface_registry.py)

Commit:

- `8ffbb3d` `Fix ESP32 JTAG probe config normalization`

## Validation

Recovered single-test runs:

- [rp2040 result](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-08-08_rp2040_pico_rp2040_gpio_signature/result.json)
- [stm32f411 result](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-03_stm32f411ceu6_stm32f411_gpio_signature/result.json)
- [stm32g431 result](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-08_stm32g431cbu6_stm32g431_gpio_signature/result.json)
- [stm32h750 result](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-09-22_stm32h750vbt6_stm32h750_wiring_verify/result.json)

Recovered full default baseline:

- [run set `2026-03-20_13-10-38`](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_13-10-38_rp2040_pico_rp2040_gpio_signature/result.json)

## Reusable Debug Lesson

When `instrument doctor` passes but `ael run` fails immediately at `preflight`,
do not assume the bench is flaky.

First compare:

- the doctor-path `probe_cfg`
- the run-plan `probe_cfg`
- the effective config for the same run

If the family-identification metadata differs, the problem is likely a
run-time config-shape regression, not an instrument-health failure.
