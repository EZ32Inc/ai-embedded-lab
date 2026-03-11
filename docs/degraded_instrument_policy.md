# Degraded Instrument Policy

## Purpose

This document defines how AEL should behave when an external instrument is unstable, partially reachable, or intermittently unusable.

It is a policy document, not only a troubleshooting note.

## Scope

This policy currently applies most directly to default verification, especially meter-backed verification paths such as ESP32-C6 with `esp32s3_dev_c_meter`.

## Core Policy

AEL should separate:

- bench degradation
- verify-stage mismatch
- core execution-model failure

The main rule is:

- do not treat degraded external instrument behavior as proof of an AEL execution-model defect

## Current Policy Buckets

### 1. `bench_degraded_fail_fast`

Used for:
- `instrument_unreachable`

Meaning:
- the required instrument path is not usable
- AEL should fail the affected worker quickly
- unrelated workers should continue
- do not spend time retrying a clearly unreachable instrument in the default worker path

### 2. `bench_degraded_retry_once`

Used for:
- `instrument_transport_unavailable`
- `instrument_api_unavailable`

Meaning:
- the instrument appears partially reachable or transiently degraded
- AEL should allow one bounded retry before failing the worker
- this is intended for short-lived transport/API instability, not long recovery flows

Current default:
- `max_attempts = 2`
- `backoff_s = 1.0`

### 3. `verify_no_retry`

Used for:
- `instrument_verify_failed`

Meaning:
- the instrument path was usable enough to reach verify
- the failure should be preserved as a verify-stage result
- default verification should not auto-retry this class immediately, because it may reflect DUT behavior, instrument behavior, or both

## Operational Meaning

For `python3 -m ael verify-default run`:

- the affected worker may retry once for transient transport/API degradation
- unreachable instruments fail fast
- verify-stage failures do not auto-retry
- unrelated workers continue independently

For `python3 -m ael verify-default repeat --limit N`:

- each worker still progresses independently
- a degraded worker stops on its own failure according to current repeat semantics
- healthy unrelated workers continue their own repeat window
- the result should expose degraded worker health clearly

## Required Result Fields

When a degraded instrument affects a worker result, AEL should preserve:

- `failure_class`
- `instrument_condition`
- `failure_scope`
- `degraded_instrument_policy`
- `retry_summary`
- `observations`

Repeat-mode aggregate payloads should also preserve:

- `health_summary`

## Failure Scope

Current intended scopes:

- `bench`
  - external instrument/network/transport degradation before verify
- `verify`
  - verify-stage failure after the instrument path was usable enough to run

These scopes are operational categories.
They are not claims about the physical root cause.

## Why This Policy Exists

Without this policy, AEL risks doing the wrong thing in both directions:

- retrying obviously broken bench paths too much
- failing too quickly on transient instrument API issues
- hiding real verify-stage failures behind automatic retries
- making operators guess whether a failure is bench-side or execution-side

## Current Limits

This is intentionally bounded:

- only one retry for transient degraded-instrument states
- no broad recovery workflow is attached yet
- no long backoff ladder is defined yet
- this policy is currently biased toward preserving signal rather than maximizing automatic recovery

## Future Extension Points

Possible future work:

- separate policy by instrument type
- richer retry/backoff settings in config
- explicit “bench degraded” termination category
- optional meter reset or recovery actions when hardware supports it

## Related Files

- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [degraded_instrument_handling.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/degraded_instrument_handling.md)
- [bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)
