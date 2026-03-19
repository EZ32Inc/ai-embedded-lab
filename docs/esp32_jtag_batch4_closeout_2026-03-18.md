# ESP32-JTAG Batch 4 Closeout

Date: 2026-03-18
Status: Complete

## Scope

This note records the Batch 4 live AEL validation outcome for the new
`esp32_jtag` backend path.

Source tracker:

- [esp32_jtag_batches_v0_1.md](./esp32_jtag_batches_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)

## Validation Target

- board: `stm32f411ceu6`
- test: `tests/plans/stm32f411_gpio_signature.json`
- control instrument: `esp32jtag_stm32f411 @ 192.168.2.103:4242`
- validation flow: `flash -> reset/run -> gpio verification`

Why this path was used:

- it is the lowest-risk representative STM32F411 baseline
- it exercises the new `esp32_jtag` control path on real hardware
- it proves both GDB-side control and HTTPS logic-analyzer verification

## Outcome

Batch 4 passed.

The live AEL path completed successfully through the current uncommitted
`esp32_jtag` backend wiring and met the initial repeatability threshold.

## Run History

Live runs completed during the closeout session:

1. `2026-03-18_20-37-54_stm32f411ceu6_stm32f411_gpio_signature`
2. `2026-03-18_20-38-11_stm32f411ceu6_stm32f411_gpio_signature`
3. `2026-03-18_20-38-46_stm32f411ceu6_stm32f411_gpio_signature`
4. `2026-03-18_20-39-15_stm32f411ceu6_stm32f411_gpio_signature`
5. `2026-03-18_20-39-41_stm32f411ceu6_stm32f411_gpio_signature`
6. `2026-03-18_20-40-08_stm32f411ceu6_stm32f411_gpio_signature`

Session result:

- `6/6` pass
- initial acceptance threshold of `5` consecutive pass runs achieved

## Observations

- preflight was stable across all runs:
  - ping OK
  - TCP `192.168.2.103:4242` OK
  - `monitor targets` OK
  - LA self-test OK
- build was stable and incremental:
  - `make: Nothing to be done for 'all'.`
- flash behavior was stable:
  - BMDA via GDB resilience ladder
  - attempt 1 succeeded on all six runs
- verification behavior was stable:
  - LA host `https://192.168.2.103:443`
  - capture passed on every run
  - observed edge counts remained in a tight band (`755` to `757`)

## Failure Notes

One earlier non-escalated attempt from the same session failed before live
validation because local sandbox policy blocked network access to
`192.168.2.103`, producing `Operation not permitted`.

Interpretation:

- this was not a bench instability signal
- this was not an `esp32_jtag` backend correctness failure
- rerunning with unrestricted network access immediately reached a stable pass path

## Batch 4 Exit Decision

Batch 4 is complete because all of the following are now true:

- one end-to-end smoke path passed through AEL
- the path used the active `esp32_jtag` backend integration
- repeated live runs reached and exceeded the `5`-pass threshold
- logs and archive output were readable enough for AI/operator review

## Recommended Next Step

Proceed to one of:

1. Batch 5 placeholder action files for `debug_halt` and `debug_read_memory`
2. Batch 6 first alignment migration against `ael/instruments/backends/stlink.py`
