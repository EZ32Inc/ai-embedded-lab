# Phase E Failure/Recovery Contract

## 1. Failure classification contract
- Introduced `ael/failure_recovery.py` with minimal failure kinds:
  - `verification_miss`
  - `verification_mismatch`
  - `instrument_not_ready`
  - `transport_error`
  - `timeout`
  - `non_recoverable`
  - `unknown`
- Added `normalize_failure_kind(...)` for stable output.

## 2. Recovery hint contract
- Added explicit lightweight recovery hint shape via `make_recovery_hint(...)`:
  - `kind`
  - `recoverable`
  - `preferred_action`
  - `reason`
  - `scope`
  - `retry`
  - `params`
  - compatibility field: `action_type`
- Added `normalize_recovery_hint(...)` used by runner before executing recovery.

## 3. Paths updated
- `ael/adapter_registry.py` representative paths:
  - `check.signal_verify`
  - `check.uart_log`
  - `check.instrument_signature`
- `ael/runner.py`:
  - stores normalized `recovery_hint` and `failure_kind` in recovery records
  - emits top-level `failure_kind` in runner result (`timeout` mapped explicitly)
- `ael/evidence.py`:
  - recovery evidence now includes `failure_kind` and `recovery_hint` facts.

## 4. Output locations
- `runs/<id>/artifacts/result.json` (runner artifact):
  - `failure_kind`
  - `recovery[]` entries with `failure_kind`, `recovery_hint`, `action_type`, `ok`
- `runs/<id>/artifacts/evidence.json`:
  - `recovery.action` items include `failure_kind` and `recovery_hint` in `facts`
- Existing top-level run `result.json` remains backward compatible.

## 5. Intentionally not yet covered
- Not all adapters/failure paths are classified yet.
- No global policy engine that chooses actions from classification.
- No multi-action recovery chains or planner.

## 6. Known limitations
- Classification is currently representative and adapter-local.
- Some failures still fall back to `unknown`.
- Recovery policy remains narrow (`reset.serial` focused) and scenario-driven.
