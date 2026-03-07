# Architecture Checkpoint Review

Date: 2026-03-07

## 1) Current Architectural State

AEL now has a practical core runtime path with explicit boundaries:

- run lifecycle anchored by `ael/__main__.py` -> `ael/pipeline.py` -> `ael/runner.py` -> `ael/adapter_registry.py`
- run contract/termination shape in `ael/run_contract.py` and runner outputs (`artifacts/run_plan.json`, `artifacts/result.json`)
- strategy boundary in `ael/strategy_resolver.py` (step shaping and runtime step config)
- evidence boundary in `ael/evidence.py` (step evidence + recovery action evidence)
- evaluator boundary for representative checks in `ael/check_eval.py`
- failure/recovery hint contract in `ael/failure_recovery.py`
- real recovery action coverage for serial reset (`reset.serial` and `control.reset.serial`)
- lightweight recovery policy boundary in `ael/recovery_policy.py` (Phase H)
- validated role-first migration examples:
  - observation facade (`observe_log` over UART backend)
  - recovery/control alias path (`control.reset.serial`)
  - mixed download-mode assist path (`control.download_mode.serial_assist`)

## 2) Reasonably Clear / Stable Boundaries

- `runner` as execution/retry/recovery loop boundary is materially clearer than earlier phases.
- `strategy_resolver` is a clear “plan shaping” boundary before execution.
- Evidence output format is stable enough for downstream AI/analysis tooling.
- Failure-kind + recovery-hint contract is explicit and reused across paths.
- Role-first migration pattern is validated by real code paths, not only docs.
- Recovery decision refinement now has a dedicated home (`recovery_policy.py`) instead of being fully scattered.

## 3) What Remains Narrow / Local / Not Yet Generalized

- Recovery policy synthesis is intentionally narrow (mainly representative UART verification-miss path).
- Evaluator coverage is still selective (`signal`, `uart`, `instrument_signature`) and not broad for every check type.
- Evidence richness remains uneven across adapters; some paths provide richer facts than others.
- Recovery action coverage is still limited; serial reset is real, but multi-action recovery is not generalized.
- Board/instrument specialization remains partly implicit in adapter behavior and config combinations.

## 4) Current Architectural Strengths

- Incremental hardening without breaking default flows.
- Compatibility-first refactoring style with wrappers/aliases.
- Real retry + recovery loop with actual hardware-facing recovery action.
- Explicit artifacts and evidence output suitable for troubleshooting and AI diagnosis.
- Role-first migration pattern already exercised on observation, control, and mixed-boundary paths.

## 5) Current Architectural Risks

- Policy sprawl risk if path-specific rules accumulate outside a small policy boundary.
- Uneven evidence depth can reduce diagnosis quality for some failures.
- Transport-specific details may creep back up if new fixes bypass role-first boundaries.
- Over-abstracting too early could slow progress and harm hardware pragmatism.

## 6) Recommended Next 2 Directions

### Direction 1: Deepen Recovery Policy Coverage (Incrementally)

- Why now: Phase H created the boundary; value now is extending it to a few more representative failure paths before it fragments.
- Problem solved: reduces ad-hoc recovery decisions and clarifies recoverable defaults/action preference semantics.
- Why better than alternatives: higher impact than broad renaming or framework work; it directly improves failure handling clarity.
- Primary type: deepening existing structure + improving board/instrument scalability.

### Direction 2: Normalize Evidence Facts Across Check Paths

- Why now: evidence contract exists, but fact quality is uneven across adapters.
- Problem solved: improves AI diagnosis reliability, post-run triage, and policy tuning quality.
- Why better than alternatives: better observability makes later planner/policy work safer; avoids premature orchestration redesign.
- Primary type: improving AI-diagnosis readiness + expanding coverage quality.

## 7) What Should NOT Be Done Next

- Do not introduce a giant generic recovery planner now.
- Do not attempt full transport abstraction across every path in one pass.
- Do not execute broad naming rewrites across the repo.
- Do not build a full board x failure x action policy matrix yet.

## One-Sentence State Of AEL Today

AEL is now a working contract-driven run pipeline with explicit runner/evidence/recovery boundaries and validated role-first migration patterns, but policy and evidence breadth are still intentionally narrow and incremental.
