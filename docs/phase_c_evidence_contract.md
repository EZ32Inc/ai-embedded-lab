# Phase C Evidence Contract

## 1. Evidence structure introduced
- Introduced a minimal structured evidence item in `ael/evidence.py`:
  - `kind`
  - `source`
  - `status` (`pass`/`fail`/`info`)
  - `summary`
  - `facts` (object)
  - `artifacts` (object)
- Added helpers:
  - `make_item(...)`
  - `collect_from_runner_result(...)`
  - `write_runner_evidence(...)`

## 2. Verification/observation paths updated
- `check.signal_verify` (`_SignalVerifyAdapter`) now emits evidence.
- `check.uart_log` (`_UartCheckAdapter`) now emits evidence.
- `check.instrument_selftest` (`_InstrumentSelftestAdapter`) now emits evidence.
- `check.instrument_signature` (`_InstrumentSignatureAdapter`) now emits evidence.

## 3. Intentionally not yet converted
- Preflight/build/load adapters are not yet converted to the new evidence item contract.
- Not all instrument backends/capability adapters produce normalized evidence directly.
- No evaluator separation was introduced in this phase.

## 4. How evidence appears in run outputs
- `pipeline.py` now writes `artifacts/evidence.json` for every run.
- Content shape:
  - `version` (`evidence/0.1`)
  - `items` (list of evidence items collected from step outputs)
- Top-level `result.json` now includes:
  - `json.evidence` path
  - `evidence` summary block (`version`, `count`, `status_counts`)

## 5. Known limitations
- Coverage is representative, not complete; non-converted paths still rely on legacy result-only fields.
- `facts` content is still adapter-specific and may be uneven across step types.
- Evidence is attached at step-result level; there is no separate evaluator model yet.
