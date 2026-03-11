# Current AEL Architecture Review

## A) Repo Structure Summary

- `ael/`
  - Core runtime CLI, pipeline orchestration, runner, adapter registry, adapters, verification helpers, run/log path management.
- `ael_controlplane/`
  - Optional control-plane package (queue worker, bridge server, task API, submit/nightly helpers).
- `configs/`
  - Probe/board/default verification configuration files.
- `tests/`
  - Test specs and plan-like JSON inputs used by runtime.
- `assets_golden/`, `assets_user/`
  - DUT/instrument assets and manifests.
- `runs/`
  - Per-run outputs (logs/json/artifacts), default run root.
- `queue/`, `reports/`
  - Control-plane queue state and reports.
- `tools/`
  - Utility scripts (cleanup, guards, smoke helpers).

## B) Real Entry Points

Core runtime:
- `ael/__main__.py:main`
  - Default CLI entry (`python3 -m ael`) for `run`, `pack`, `doctor`, `verify-default`, `instruments`, `dut`.
- `ael/pipeline.py:run_pipeline`
  - Main orchestration entry for a hardware run.
- `ael/pipeline.py:main`
  - Direct pipeline CLI entry (`python3 -m ael.pipeline run ...`).
- `ael/default_verification.py:run_default_setting`
  - Executes configured default verification modes.

Optional control-plane:
- `ael_controlplane/__main__.py:main`
  - Control-plane CLI (`submit`, `bridge`, `up`, `status`, `nightly`).
- `ael_controlplane/bridge_server.py:run_server`
  - HTTP bridge server.
- `ael_controlplane/task_api.py:main` and `run_server`
  - HTTP task-ingest API server.
- `ael_controlplane/agent.py:run_sweep`
  - Queue task runner/worker loop.
- `ael/cli.py:main`
  - Standalone submit client.

Notes:
- There is no separate legacy `orchestrator.py` runtime entry in current core path.
- Effective orchestrator is `ael/pipeline.py` + `ael/runner.py`.

## C) Actual Run Lifecycle

1. Receive run request
- `ael/__main__.py:main` (`run` command)
- Resolves board/control-instrument/test input and calls `ael.pipeline.run_cli`.

2. Load config/spec/profile-like inputs
- `ael/pipeline.py:run_pipeline`
- Loads test JSON, control-instrument config, board YAML; merges into effective config.

3. Prepare execution plan
- `ael/pipeline.py:run_pipeline`
- Builds `runplan/0.1` structure and step list (`preflight`, `build`, `load`, `check_*`).

4. Execute build/flash/verify sequence
- `ael/runner.py:run_plan`
- Executes steps via `ael/adapter_registry.py:AdapterRegistry.get` and concrete adapters.

5. Retry and recovery
- `ael/runner.py:_retry_budget`, per-step retry loop in `run_plan`
- Optional recovery hook via `recovery_hint` and `registry.recovery(...)`.

6. Pass/fail and return code
- Runner determines step success/failure.
- `ael/pipeline.py:_code_from_failed_step` maps failed step to process exit code.

7. Report and artifact storage
- Runner writes `artifacts/run_plan.json` and `artifacts/result.json`.
- Pipeline writes top-level `result.json`, `meta.json`, log/json pointers, and copied firmware artifacts.

## D) Main Orchestration Logic

- Sequencing and plan assembly:
  - `ael/pipeline.py:run_pipeline`
- Step execution and retries:
  - `ael/runner.py:run_plan`
- Adapter dispatch:
  - `ael/adapter_registry.py:AdapterRegistry`
- Result packaging and run metadata:
  - `ael/pipeline.py:run_pipeline`
  - `ael/run_manager.py:create_run`

## E) Current Boundary Split (As Implemented)

- Orchestration/core-like logic:
  - `ael/__main__.py`, `ael/pipeline.py`, `ael/runner.py`, `ael/default_verification.py`
- Board-specific logic:
  - `configs/boards/*.yaml`, board-dependent handling inside pipeline step shaping
- Toolchain-specific logic:
  - `ael/adapters/build_cmake.py`, `build_idf.py`, `build_stm32.py`
- Flash/programming logic:
  - `ael/adapters/flash_bmda_gdbmi.py`, `flash_idf.py`
- Instrument/measurement logic:
  - `ael/adapters/preflight.py`, `observe_gpio_pin.py`, `observe_uart_log.py`, `instrument_*.py`, `ael/verification/la_verify.py`
- Reporting/logging/results:
  - `ael/run_manager.py`, `ael/pipeline.py`, `ael/evidence.py`, notifier modules

## F) Current Strengths

- Clear default CLI entry and deterministic command surface.
- Real execution plan object (`runplan/0.1`) passed to a generic runner.
- Retry logic is centralized in runner with explicit precedence.
- Adapter registry provides a practical execution boundary.
- Per-run artifacts are structured and reproducible under `runs/<run_id>/`.
- Control-plane functionality is separated into `ael_controlplane/` package.

## G) Current Pain Points

- `ael/pipeline.py` still mixes orchestration with strategy details (build/flash/verify branching).
- Recovery framework exists, but default recovery action is mostly noop.
- No first-class run-level timeout termination in core runner.
- Case/profile concepts are implicit (board/control-instrument/test inputs) rather than explicit typed entities.
- Multiple entry surfaces (`ael`, `ael.pipeline`, `ael_controlplane`, `ael.cli`) can be confusing without a single canonical architecture doc.
