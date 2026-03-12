# Generated Example Runtime Readiness Review

## Purpose

Define how to decide whether a generated example is meaningfully runnable on the
current bench, without confusing readiness with actual runtime validation.

## When to use

Use this workflow when:

- a generated example exists and is already plan/build valid
- the next question is whether live runtime validation should be attempted now
- the bench setup or external stimulus may still be incomplete

## Required distinction

Keep these concepts separate:

- `runtime_validation_status`
  - what has actually been proven by live runs
- `runtime_validation_basis`
  - what kind of live attempt, if any, has happened
- `runtime_readiness_status`
  - whether a live run is meaningful to attempt now

Do not promote runtime-validation status just because an example looks
well-formed on paper.

## Readiness categories

### `runtime_ready_now`

Use when:

- the formal connection contract is complete
- the required bench setup exists
- no known blocking bench condition is preventing a meaningful run

### `blocked_missing_bench_setup`

Use when:

- the example is formally complete enough for retrieval
- but the required runtime bench path is not actually provisioned yet

Examples:

- missing UART bridge/wiring
- selected host serial path not actually attached to the intended DUT

### `blocked_unbound_external_input`

Use when:

- the formal contract explicitly leaves an external stimulus undefined
- the example is therefore not ready for stronger runtime claims

Example:

- ADC input declared, but analog source intentionally `not_defined`

### `blocked_unstable_bench_path`

Use when:

- the example is formally runnable
- but a known unstable bench path makes runtime attempts unreliable or currently
  blocked

Example:

- ESP32-C6 example depending on a currently unstable meter-backed bench path

## Review method

1. `inventory describe-test`
2. `explain-stage --stage plan`
3. inspect formal connection contract
4. check whether the current bench setup really exists
5. classify readiness conservatively

## Notes

- Readiness is a planning/status concept, not proof of runtime success.
- If a live run is attempted and blocked, update the runtime-validation basis
  without overstating the runtime-validation status.
