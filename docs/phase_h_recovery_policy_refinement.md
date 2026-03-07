# Phase H: Recovery Policy Refinement

Date: 2026-03-07

## 1) Policy Boundary Introduced

Added lightweight module: `ael/recovery_policy.py`.

This module centralizes small recovery-decision rules without introducing a full planner.

## 2) Representative Decisions Centralized

- Default recoverability by `failure_kind` (narrow, explicit).
- Recovery hint interpretation:
  - honor normalized explicit hints
  - skip hints marked non-recoverable
- Default action synthesis (narrow case):
  - for `check.uart_log` + `verification_miss` + known UART port, synthesize `reset.serial`.
- Action attempt cap for representative recovery actions:
  - `reset.serial` / `control.reset.serial` capped to one attempt per run.

## 3) failure_kind / recovery_hint / preferred_action Interpretation

- `runner` now asks `recovery_policy.resolve_hint(step, step_out)` for one normalized recovery decision source.
- If no hint exists, policy may synthesize one for the representative UART verification-miss path.
- Action selection still uses existing hint fields (`preferred_action`/`action_type`) and existing adapter lookup.
- Existing allow-list checks remain enforced by runner policy (`recovery_policy.allowed_actions` in plan).

## 4) Intentionally Out Of Scope

- No full recovery planner.
- No broad board-specific policy matrix.
- No multi-step recovery orchestration.
- No broad adapter architecture changes.

## 5) Known Limitations

- Default hint synthesis is intentionally narrow (`check.uart_log` path only).
- Action caps are only defined for representative serial reset actions.
- Some recovery decisions remain step-specific and will require future incremental cleanup.
