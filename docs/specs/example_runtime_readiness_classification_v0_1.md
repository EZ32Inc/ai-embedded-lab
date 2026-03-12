# Example Runtime Readiness Classification v0.1

This note defines the bounded runtime-readiness categories used for generated
examples.

## Purpose

Runtime-readiness answers:

> Is this generated example meaningfully runnable on the current bench now?

It does not answer:

> Has this example already been runtime-validated?

## Categories

### `runtime_ready_now`

The example is formally complete and the known current bench setup is adequate
for a meaningful live attempt.

### `blocked_missing_bench_setup`

The example is formally complete, but its required runtime bench path has not
been provisioned or confirmed.

### `blocked_unbound_external_input`

The example intentionally leaves a required external input undefined, so runtime
claims should remain deferred.

### `blocked_unstable_bench_path`

The example is formally runnable, but a known unstable bench dependency makes
current live attempts unreliable or currently blocked.

## Relationship to validation fields

Use runtime-readiness together with, not instead of:

- `runtime_validation_status`
- `runtime_validation_basis`

## Current bounded use

This classification is intended for generated examples during bounded expansion
work. It should remain conservative and should not be treated as a broad bench
or inventory model rewrite.
