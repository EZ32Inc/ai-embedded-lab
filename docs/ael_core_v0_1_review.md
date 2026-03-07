# AEL Core v0.1 Review (Current Repo)

This review follows `ael_core_v0_1_boundary_and_codex_prompt.md`, with one update:
- Some "entry point" examples in that prompt are older. In current repo, control-plane code is in `ael_controlplane/` (optional), while default CLI remains in `ael/`.

## Task 1 - Core Entry Points

Primary core entry points:
- `ael/__main__.py:28` `main()`
  - Default CLI (`python3 -m ael`) with commands `run`, `pack`, `doctor`, `verify-default`, `instruments`, `dut`.
- `ael/pipeline.py:365` `run_pipeline(...)`
  - Main run execution entry for hardware runs.
- `ael/pipeline.py:933` `run_cli(...)`
  - Thin wrapper used by CLI `run` path.
- `ael/default_verification.py:155` `run_default_setting(...)`
  - Orchestrates default verification presets/sequence.

Optional control-plane entry points (not required by default core CLI):
- `ael_controlplane/agent.py` (agent worker)
- `ael_controlplane/task_api.py:142` `main()` (task ingest API)
- `ael_controlplane/bridge_server.py` (bridge API)
- `ael/cli.py:52` `main()` (submit helper)

`run(case, profile)` equivalent:
- No single function named `run(case, profile)`.
- Practical equivalent is `run_pipeline(probe_path, board_arg, test_path, ...)` in `ael/pipeline.py:365`.

## Task 2 - Run Lifecycle Verification

Lifecycle coverage in current code:
- Receive run request: Yes
  - `ael/__main__.py:99-169`
- Load case (test spec): Yes
  - `ael/pipeline.py:380-384` (loads test JSON)
- Load profile/environment (probe+board): Yes
  - `ael/pipeline.py:408-410`, `428-433`
- Generate execution plan: Yes
  - `ael/pipeline.py:523-776`
- Execute steps: Yes
  - `ael/runner.py:199-307`
- Retry if needed: Yes
  - `ael/runner.py:70-95`, `245-276`
- Terminate pass/fail: Yes
  - `ael/runner.py:302-307`, `ael/pipeline.py:834-919`
- Produce result package: Yes
  - `ael/pipeline.py:788-817`, `823-833`

## Task 3 - Core vs Adapter Separation

What is correctly separated:
- Core orchestrates plan/flow/retry/result:
  - `ael/pipeline.py`, `ael/runner.py`
- Toolchain and flashing command execution is in adapters:
  - build: `ael/adapters/build_cmake.py`, `build_idf.py`, `build_stm32.py`
  - flash: `ael/adapters/flash_bmda_gdbmi.py`, `flash_idf.py`
- Verification implementations are in adapters/helpers:
  - `ael/adapters/observe_gpio_pin.py`, `ael/verification/la_verify.py`

Boundary pressure/violations (minor to moderate):
- Core pipeline contains method-specific branching and wiring policy logic:
  - e.g. idf/esptool selection and flash config shaping in `ael/pipeline.py:626-646`
  - verify strategy branching (meter digital vs LA signal) in `ael/pipeline.py:686-749`
- Core pipeline includes instrument selftest parameterization details:
  - `ael/pipeline.py:544-576`

Impact:
- Core changes are more likely when adding new execution variants.

## Task 4 - Execution Plan Implementation

AEL does use an explicit execution plan object:
- Constructed in `ael/pipeline.py:751-776` (`version: runplan/0.1`, `steps`, `recovery_policy`, `report`)
- Executed by generic runner in `ael/runner.py:199-307`

Conclusion:
- Not a purely hard-coded linear flow; it is plan-driven with step adapters.

## Task 5 - Retry Mechanism

Retry mechanism exists and is centralized:
- Retry budget computation:
  - `ael/runner.py:70-95`
  - precedence: `step.retry_budget` > `plan.recovery_policy.retries` > defaults
- Attempt loop:
  - `ael/runner.py:250-276`
- Recovery hook path:
  - `ael/runner.py:283-297`

Failure classification:
- Step class mapping (`build/load/run/check/preflight/plan`):
  - `ael/runner.py:37-51`
- CLI exit code mapping by failed step prefix:
  - `ael/pipeline.py:496-511`

Gap:
- `recovery_policy` action is currently mostly placeholder (`reset.serial` -> noop):
  - `ael/adapter_registry.py:589-591`, `507-510`

## Task 6 - Run Termination Conditions

Supported today:
- `pass`: yes (`runner_result.ok` true)
  - `ael/runner.py:302-307`, `ael/pipeline.py:834-859`
- `fail`: yes (step failure or lookup/execute errors)
  - `ael/runner.py:241-243`, `299-300`

Partially/implicitly supported:
- `safety_abort`: partial via execution guard limit
  - `ael/runner.py:223-229` (`execution guard limit reached`)

Missing as first-class core conditions:
- `timeout` at run-level: not explicitly modeled in core runner/pipeline.
  - Timeouts exist in some adapters/subprocess calls, but no global run timeout contract.

## Task 7 - Result Artifact System

Structured per-run artifacts are produced:
- Run directory creation and standard paths:
  - `ael/run_manager.py:100-126`
- Deterministic runs root default:
  - `ael/paths.py:11-18`
- Runner artifacts:
  - `artifacts/run_plan.json`, `artifacts/result.json` (`ael/runner.py:204`, `307`)
- Pipeline outputs:
  - `result.json`, `meta.json`, logs map/json map (`ael/pipeline.py:788-817`, `823-833`)
- Firmware copies into run artifacts:
  - `ael/pipeline.py:783`, via `_copy_artifacts`

Conclusion:
- Yes, structured and reproducible per-run storage is implemented.

## Task 8 - Boundary Violations

1) Core-level branching contains execution-strategy specifics
- Location: `ael/pipeline.py:626-749`
- Problem: pipeline decides detailed flash/verify mode paths.
- Impact: core changes may be needed for new methods.
- Minimal fix: move strategy resolution into adapter registry policy helper (data-driven mapping).

2) Instrument selftest defaults and parameter shaping in core pipeline
- Location: `ael/pipeline.py:544-576`
- Problem: non-core detail in orchestration layer.
- Impact: instrument variants can force core edits.
- Minimal fix: pass raw selftest config through and let adapter/backend apply defaults.

3) Recovery framework exists but action implementation is noop
- Location: `ael/adapter_registry.py:507-510`, `589-591`
- Problem: retry recovery path is architecturally present but operationally weak.
- Impact: repeated failures are less recoverable.
- Minimal fix: implement one real recovery action (`reset.serial` or `control.reset_target`) in adapter layer.

## Task 9 - Minimal Improvements

1. Introduce a thin typed run request object for `run_pipeline(...)` inputs
- Keep behavior; improve boundary clarity (`case/profile` style mapping).

2. Move flash/verify strategy selection out of `pipeline.py` into registry/policy helper
- Keep the existing step types; reduce core branching.

3. Add explicit run-level timeout in runner
- Add optional `plan.timeout_s`; fail with explicit timeout reason.

4. Add explicit termination enum in result payload
- e.g. `termination: pass|fail|timeout|safety_abort` in runner and top-level result.

5. Implement at least one non-noop recovery adapter action
- Keep policy format unchanged; improve real retry effectiveness.

## Overall Verdict

- Core v0.1 intent is mostly implemented:
  - plan-driven orchestration, adapter execution, retry loop, and structured artifacts are present.
- Main gaps to fully match boundary spec:
  - no first-class run timeout termination,
  - limited real recovery actions,
  - some strategy/detail logic still lives in core pipeline instead of adapter/policy boundaries.
