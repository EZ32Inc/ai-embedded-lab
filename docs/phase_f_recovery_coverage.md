# Phase F Recovery Coverage

## 1. Recovery scenarios now covered
- Existing Phase D:
  - `check.signal_verify` fail-first injection -> `reset.serial` -> retry success.
- New Phase F:
  - `check.uart_log` fail-first injection -> `reset.serial` -> retry success.
  - `check.signal_verify` fail-first injection + forced fail-after-recovery -> final fail.

## 2. Recoverable-to-success scenarios
- Signal verify fail-first demo (Phase D).
- UART verify fail-first demo (Phase F).

## 3. Recovery-attempted-but-final-fail scenarios
- Signal verify demo with `fail_after_recovery: true` (Phase F).

## 4. Recovery actions used
- `reset.serial` (real RTS pulse reset via serial adapter).

## 5. Reused contracts
- `failure_kind` contract from Phase E.
- `recovery_hint` contract from Phase E.
- Recovery action recording in runner `recovery[]`.
- Evidence recording in `artifacts/evidence.json` including `recovery.action`.

## 6. Intentionally deferred
- No generic recovery planner.
- No broad cross-adapter action policy.
- No evaluator/decision-engine separation.

## 7. Known limitations
- New scenarios are deterministic demo/test paths, not broad physical fault handling.
- Coverage is still representative, not exhaustive across all adapters.
- Some real-world transport failures remain environment-dependent and may not always be recoverable by `reset.serial`.
