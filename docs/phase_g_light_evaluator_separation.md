# Phase G Light Evaluator Separation

## 1. Representative paths updated
- `check.signal_verify`
- `check.uart_log`
- `check.instrument_signature`

## 2. Fact/evaluation boundary introduced
- Check adapters now prepare explicit fact dictionaries first (observation/measurement facts).
- Verdict-style pass/fail and failure-kind decisions are computed by a small evaluator helper module.
- Adapters keep execution/IO and evidence emission; evaluator handles judgment logic.

## 3. Helper/module added
- Added `ael/check_eval.py` with focused helpers:
  - `evaluate_signal_facts(...)`
  - `evaluate_uart_facts(...)`
  - `evaluate_instrument_signature_facts(...)`

## 4. What remained inside existing checks
- Raw hardware/transport interactions.
- Recovery demo fail-first/fail-after-recovery injections.
- Output file writing and evidence payload construction.

## 5. Compatibility preservation
- Existing result/evidence schemas remain compatible (additive `facts` in step outputs).
- Existing failure/recovery contracts from Phase E remain in use.
- Existing recovery flows (Phase D/F) continue to use the same `recovery_hint`/`reset.serial` path.
- Default verification flow remains unchanged in behavior.

## 6. Intentionally deferred
- No full evaluator framework or plugin model.
- Not all check paths converted.
- No general observation model abstraction.

## 7. Known limitations
- Some coupling still exists in adapters (they still map evaluator output into step/result/evidence shapes).
- Evaluator coverage is representative only; broader conversion can be done in later phases.
