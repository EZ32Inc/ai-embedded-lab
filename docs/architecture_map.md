# Architecture Map (Current AEL Repo)

## 1) Entry points

- `ael/__main__.py:main`
  - Main CLI entry (`python3 -m ael`), dispatches `run`, `pack`, `doctor`, `bridge`, `up`, `status`, `nightly`, `verify-default`, etc.
- `ael/pipeline.py:main`
  - Runtime pipeline CLI (`run`) and home of `run_pipeline` execution path.
- `ael/agent.py:main`
  - Queue worker entry; processes tasks from `queue/inbox` to `queue/done|failed` via `run_sweep`.
- `ael/task_api.py:main`
  - HTTP task ingest API (`/v1/tasks`) writing tasks into queue inbox.
- `ael/bridge_server.py:main`
  - Bridge API server for task submit/status/result/artifact/stream endpoints.
- `ael/submit.py:submit_to_bridge` (used by CLI `ael submit`)
  - Natural-language/JSON submit helper to bridge API.

## 2) One run lifecycle (hardware run path)

Path traced from `ael run`:

- Receive task/input:
  - `ael/__main__.py:main` (`run` subcommand)
- Prepare context/spec:
  - `ael/config_resolver.py:resolve_probe_config`
  - `ael/pipeline.py:run_cli` -> `run_pipeline`
  - merges probe + board + test into effective config and creates run paths.
- Generate code or plan:
  - For hardware `ael run`, a runtime plan is assembled in `ael/pipeline.py:run_pipeline` (`plan` dict, not LLM codegen).
  - Agent/bridge codegen/planning appears in `ael/agent.py` + `ael/planner.py` + `ael/codex_driver.py`.
- Build:
  - `ael/runner.py:run_plan` executes `build.*` step through `ael/adapter_registry.py:_BuildAdapter`
  - adapter implementations in `ael/adapters/build_cmake.py`, `build_idf.py`, `build_stm32.py`.
- Flash:
  - `load.*` step via `_LoadAdapter` in `ael/adapter_registry.py`
  - implementations in `ael/adapters/flash_bmda_gdbmi.py` or `flash_idf.py`.
- Verify:
  - `check.signal_verify` via `_SignalVerifyAdapter` (`observe_gpio_pin.run` + `ael/verification/la_verify.py`)
  - or `check.instrument_signature` / `check.instrument_selftest` for instrument-based flows.
- Retry if needed:
  - Step retries handled in `ael/runner.py` (`_retry_budget`, per-step retry loop).
  - Recovery action hook handled in `ael/runner.py:_run_recovery` (currently `reset.serial` maps to noop recovery adapter).
- Report result:
  - Runner writes `artifacts/run_plan.json` and `artifacts/result.json`.
  - Pipeline layer writes top-level `result.json`, `meta.json`, and log/json pointers.

## 3) Main components

- Orchestration CLI:
- `ael/__main__.py`, `ael/pipeline.py`
- Generic plan runner:
  - `ael/runner.py` (step execution, retry/recovery loop)
- Adapter registry + dispatch:
  - `ael/adapter_registry.py`
- Build/flash/observe adapters:
  - `ael/adapters/*`
- Agent/queue runner:
  - `ael/agent.py`, `ael/queue.py`
- Bridge/API ingest and task control plane:
  - `ael/bridge_server.py`, `ael/task_api.py`, `ael/bridge_task.py`, `ael/submit.py`
- Planning/Codex integration:
  - `ael/planner.py`, `ael/codex_driver.py`
- Reporting/artifacts:
  - `ael/run_manager.py`, `ael/reporting.py`
- Config/policy resolution:
  - `ael/config_resolver.py`, `configs/boards/*.yaml`, `configs/*.yaml`, `tests/plans/*.json`

## 4) Communication/call relationships

- Direct Python calls:
  - CLI -> pipeline -> runner -> adapter registry -> adapter modules.
- Subprocess calls:
  - Build/flash invoke `cmake`, `idf.py`, `gdb` via adapters.
- HTTP calls:
  - `task_api` and `bridge_server` expose HTTP endpoints.
  - LA/instrument adapters call HTTP device APIs.
- Filesystem JSON/log artifacts:
  - Queue states in `queue/inbox|running|done|failed`.
  - Run artifacts in `runs/<run_id>/...` (`*.log`, `*.json`, `artifacts/*`).
- Device/probe interfaces:
  - SWD/GDB, serial UART, logic analyzer web API, instrument TCP/HTTP adapters.

## 5) Core vs adapter split

**Core orchestration**

- `ael/__main__.py`
- `ael/pipeline.py`
- `ael/runner.py`
- `ael/agent.py`
- `ael/queue.py`
- `ael/bridge_server.py`
- `ael/task_api.py`
- `ael/config_resolver.py`
- `ael/reporting.py`
- `ael/run_manager.py`

**Adapters / board-specific / tool-specific layers**

- `ael/adapter_registry.py` (dispatch + adapter wiring; sits at boundary)
- `ael/adapters/*` (build/flash/observe/instrument implementations)
- `ael/verification/la_verify.py` (signal metrics helper)
- `configs/boards/*.yaml` + test specs under `tests/plans/*.json` (hardware-specific behavior selection)

## Immediate pain points noticed

- Orchestration boundaries are mixed: `ael/pipeline.py` both composes plan and writes final reports.
- Retry policy fields in plan (`recovery_policy.retries`) appear separate from actual retry decisions in `ael/runner.py` (`_retry_budget`), which can drift.
- Recovery framework exists but default recovery is mostly noop (`reset.serial`).
- Bridge/task-agent flow and direct `ael run` flow both execute plans but through different pre-processing paths.

---

## Non-goals

- No architecture redesign.
- No file/module renaming.
- No behavior changes; this is a map of current implementation.
