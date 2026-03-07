# Phase A Run Contract

## 1) What Was Added

- RunRequest
  - Added thin input object `RunRequest` in `ael/run_contract.py`.
  - Covers current top-level inputs: probe, board, test, wiring, output mode, skip/build flags, timeout.

- Termination states
  - Added standardized termination contract in `ael/run_contract.py`:
    - `pass`, `fail`, `timeout`, `safety_abort`.
  - Runner now emits one of these states.

- Timeout handling
  - Added run-level timeout field (`timeout_s`) support in runner plan execution.
  - Runner sets termination to `timeout` when elapsed runtime exceeds configured timeout.

- Result schema updates
  - Top-level run result now includes explicit lifecycle fields:
    - `run_id`, `termination`, `success`, `started_at`, `ended_at`, `timeout_s`, `retry_summary`.
  - Existing fields (`ok`, logs/json/artifacts, failed_step, error_summary) were preserved.

## 2) Files Changed

- `ael/run_contract.py`
  - New: `RunRequest` dataclass and termination constants.

- `ael/runner.py`
  - Added timeout-aware loop checks.
  - Added standardized `termination` in runner result.
  - Marked guard-limit exits as `safety_abort`.

- `ael/pipeline.py`
  - Added optional `run_request` input path for `run_pipeline`.
  - Added timeout resolution from request/test config into plan (`timeout_s`).
  - Extended top-level result JSON with lifecycle fields and standardized termination.
  - Added timeout/safety-abort specific process exit mapping.

- `tests/test_runner_retry_policy.py`
  - Added tests for pass termination and timeout termination behavior.

## 3) Intentionally Deferred

- Full Case/Profile domain model.
- Full strategy resolver extraction from pipeline.
- Full evidence contract rollout across all checks.
- Rich `safety_abort` semantics beyond guard-limit handling.

## 4) Known Limitations

- Timeout behavior is soft at step boundaries:
  - If an adapter call blocks internally, runner cannot hard-interrupt it.
  - Timeout is enforced before/after step attempts in current synchronous flow.
- `safety_abort` is currently used for guard-limit protection, not broader safety policy logic.
