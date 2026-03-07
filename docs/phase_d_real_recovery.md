# Phase D Real Recovery

## 1. Recovery scenario chosen
- Representative verify path: `check.signal_verify`.
- Scenario: an opt-in fail-first verify injection forces the first signal verify attempt to fail, then recovery runs, then retry succeeds.

## 2. How failure is injected
- Injection is test-only/opt-in via verify step input:
  - `inputs.recovery_demo.fail_first: true`
- Implemented in `_SignalVerifyAdapter` using runtime state so it fails only once per run/step.
- Default runs are unaffected because `recovery_demo` is absent by default.

## 3. Recovery action implemented
- Implemented real recovery adapter for `reset.serial`:
  - opens serial port with `pyserial`
  - toggles RTS pulse
  - waits settle delay
  - closes port
- Action parameters are passed through `recovery_hint.params` (`port`, `baud`, `pulse_ms`, `settle_ms`).

## 4. How success is verified
- Recovery flow visibility:
  - `runner` step log shows first `check.signal_verify` failure and next-attempt success.
  - `runner.recovery[]` records executed action and result.
  - `result.json` keeps retry/recovery summary (`recovery_attempts`).
  - `artifacts/evidence.json` now includes `recovery.action` item and verify evidence items.

## 5. Intentionally deferred
- No general recovery planner.
- No broad failure taxonomy.
- No multi-step recovery chain orchestration.
- No conversion of all step types to recovery-aware hints.

## 6. Known limitations
- This is a narrow, opt-in demo path centered on signal verify.
- Recovery action requires serial access and valid port for real hardware runs.
- Recovery evidence is summary-level and not yet tied to a richer causal model.
