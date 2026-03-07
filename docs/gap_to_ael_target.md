# Gap to AEL Target

Target direction considered:
- AI-controlled embedded development + hardware verification loop
- clear orchestration vs board/tool/instrument separation
- toward Core/Skills/Adapters (and potentially Action/Observation/Evidence/Evaluator later)

## A) What Already Exists Today

- Real orchestration runtime exists (`ael/pipeline.py` + `ael/runner.py`).
- Explicit execution plan object exists (`runplan/0.1`).
- Retry mechanism exists and is centralized in runner.
- Adapter registry and adapter modules are in place.
- Verification paths exist (signal verify, instrument signature/selftest, UART checks).
- Structured per-run outputs exist under `runs/<run_id>/`.
- Optional control-plane exists as separate package (`ael_controlplane/`).

## B) What Is Missing

- No first-class typed `case/profile` run abstraction in core API.
- No explicit run-level timeout contract in runner.
- No explicit termination enum (`pass/fail/timeout/safety_abort`) in standard result schema.
- Recovery actions are not yet fully operational (default action is noop).
- Evidence model exists (`ael/evidence.py`) but is not yet a strong, consistent runtime contract across all checks.

## C) What Is Mixed Together Today

- `ael/pipeline.py` mixes orchestration with some strategy details (flash method, verify mode branches, selftest defaults).
- Board/tool/instrument shaping logic appears partly in core pipeline and partly in adapters.
- Result packaging is mostly good, but responsibilities are split across runner and pipeline in ways that are not yet a single schema-first contract.

## D) Minimal Next Improvements (Top 5)

1. Add explicit run-level timeout in runner
- Change: support `plan.timeout_s` in `ael/runner.py`.
- Why: gives deterministic timeout termination across all runs.
- Where: `ael/runner.py`.
- Risk: Low.

2. Add `termination` field to runner and top-level results
- Change: emit one of `pass|fail|timeout|safety_abort`.
- Why: makes run outcomes machine-consumable and uniform.
- Where: `ael/runner.py`, `ael/pipeline.py` result composition.
- Risk: Low.

3. Move strategy selection helper(s) out of `pipeline.py`
- Change: keep plan orchestration in pipeline, move board/tool-specific decision mapping into a dedicated policy/helper module.
- Why: improves core boundary without changing adapter behavior.
- Where: new helper near `ael/adapter_registry.py` or `ael/config_resolver.py`.
- Risk: Medium.

4. Implement one real recovery action
- Change: implement non-noop `reset.serial` or equivalent adapter recovery.
- Why: converts retry/recovery from structural to practical.
- Where: `ael/adapter_registry.py` + adapter module.
- Risk: Medium.

5. Formalize case/profile input object (thin wrapper)
- Change: add a small typed structure for resolved run inputs before plan generation.
- Why: clarifies boundary toward Core/Skills/Adapters without major refactor.
- Where: `ael/pipeline.py` (and possibly a new `ael/run_request.py`).
- Risk: Low.

## Short Summary

- What AEL is today:
  - A working plan-driven hardware orchestration engine with adapters, retries, and structured per-run artifacts.

- What AEL is closest to becoming next:
  - A cleaner core/adapters architecture with explicit run contracts and stronger recovery/termination semantics.

- What should be done first:
  - Add run timeout + explicit termination fields, then implement one real recovery action.
