# Generated Example Execution Handoff v0.1

## Purpose

This note is a short handoff from the current generated-example governance work
to the next execution-oriented work.

It answers:

> If governance is good enough now, what should the next execution work be?

## Worth Doing Next

### 1. Provision one UART runtime path on RP2 or STM32

Best target class:
- one generated UART example on a family that is structurally strong and only
  blocked by missing bench setup

Why:
- this is the cleanest path from `blocked_missing_bench_setup` to `ready_now`

### 2. Define one concrete ADC external-input contract

Best target class:
- one ADC example on any currently generated family

Why:
- it turns one intentionally unbound input into a real runtime candidate

### 3. Keep ESP32 generated-example runtime claims conservative

Why:
- the current meter-backed bench path is still unstable enough to distort
  repeatability

## Not Worth Doing Yet

- another broad governance pass
- broad USB example expansion
- broad new-vendor family expansion
- broad runtime validation across all generated examples

## Practical Rule

Prefer the next execution task that removes one real blocker:
- missing bench setup
- missing external input contract

Do not prefer tasks that only add more governance structure around already
understood blockers.
