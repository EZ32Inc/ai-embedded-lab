# Generated Example Runtime Validation

## Purpose

Use this workflow when a generated example already exists and the goal is to move it from:

- generated
- plan/build-valid

to:

- runtime-validated on real bench hardware

## Authoritative Order

For generated-example runtime validation, use this order:

1. `inventory describe-test`
2. `explain-stage --stage plan`
3. build smoke / build validity
4. live run on the real bench
5. conservative catalog/status update

Do not skip directly from source inspection to claiming runtime validation.

## Selection Rule

Prefer first-batch runtime validation on examples that:

- have a formal connection contract
- do not depend on undefined external analog stimulus
- already match current bench wiring
- have a simple expected outcome

Typical first candidates:

- UART banner examples

Defer higher-risk examples until the contract and bench are clearer:

- ADC examples with unbound external analog input
- USB examples

## Required Outputs

Before claiming runtime validation, confirm:

- plan resolution is coherent
- build path is coherent
- the live run completed on real hardware
- the observed result matches the example’s intended behavior

## Status Update Rule

Update the example catalog conservatively.

Suggested mapping:

- plan + build only:
  - `validation_status = build_and_plan_verified`
  - `runtime_validation_status = not_run`
  - `runtime_validation_basis = not_attempted`

- one successful real bench run:
  - `validation_status = hardware_verified_single`
  - `runtime_validation_status = hardware_verified_single`
  - `runtime_validation_basis = live_bench_run`

- real bench run attempted but blocked by bench/instrument conditions:
  - keep `validation_status = build_and_plan_verified`
  - keep `runtime_validation_status = not_run`
  - set `runtime_validation_basis = live_bench_attempt_failed`
  - record a short runtime-validation note

- repeated successful real bench runs:
  - `validation_status = hardware_verified_repeated`
  - `runtime_validation_status = hardware_verified_repeated`
  - `runtime_validation_basis = live_bench_repeat`

## Connection Contract Rule

Answer runtime-connection questions from formal sources first:

1. `inventory describe-test`
2. test plan
3. board profile

Use firmware source only to explain missing contract data.

## Stopping Rule

If the bench contract is incomplete or the physical setup is unclear:

- stop at plan/build-valid
- record the blocking gap explicitly
- do not upgrade the example to runtime-validated
