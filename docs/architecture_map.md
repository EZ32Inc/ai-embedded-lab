# Architecture Map (Current AEL Repo)

## 1) Entry points

- `ael/__main__.py:main`
  - Main CLI entry (`python3 -m ael`) with core commands:
    - `run`, `pack`, `doctor`, `verify-default`, `instruments`, `dut`
- `ael/pipeline.py:main`
  - Secondary CLI entry for direct pipeline run (`python3 -m ael.pipeline run ...`).
- `ael/default_verification.py:run_default_setting`
  - Called by `ael verify-default run`; supports `none`, `preflight_only`, `single_run`, `sequence`.
- `ael_controlplane/*` (optional package, not part of default `ael` CLI)
  - `agent.py`, `task_api.py`, `bridge_server.py`, `submit.py`
- `ael/cli.py:main`
  - Standalone submit helper (`python3 -m ael.cli submit ...`) for control-plane API.

## 2) One run lifecycle (hardware run path)

Path traced from `python3 -m ael run ...`:

- Parse and resolve CLI input:
  - `ael/__main__.py:main`
  - board/probe resolution via `ael/config_resolver.py`
- Start pipeline:
  - `ael/pipeline.py:run_cli` -> `run_pipeline`
  - run directory created by `ael/run_manager.py:create_run`
- Build runtime plan:
  - `run_pipeline` creates a `plan` dict and `steps` (`preflight`, `build`, `load`, `check_*`).
- Execute plan:
  - `ael/runner.py:run_plan` with retries/recovery hooks.
  - adapter dispatch via `ael/adapter_registry.py`.
- Build/flash/check:
  - build adapters in `ael/adapters/build_*`
  - flash adapters in `ael/adapters/flash_*`
  - verify/observe adapters in `ael/adapters/*` + `ael/verification/la_verify.py`
- Persist outputs:
  - runner artifacts: `artifacts/run_plan.json`, `artifacts/result.json`, `artifacts/runtime_state.json`
  - run-level outputs: `result.json`, `meta.json`, logs/json pointers, copied firmware artifacts.

## 3) Main components

- Core CLI/orchestration:
  - `ael/__main__.py`, `ael/pipeline.py`, `ael/default_verification.py`
- Plan runner:
  - `ael/runner.py`
- Adapter registry/boundary:
  - `ael/adapter_registry.py`
- Build/flash/observe implementations:
  - `ael/adapters/*`
- Verification helpers:
  - `ael/verification/la_verify.py`
- Run/log path management:
  - `ael/run_manager.py`, `ael/paths.py`
- Config and asset resolution:
  - `ael/config_resolver.py`, `ael/assets.py`, `configs/*.yaml`, `tests/plans/*.json`
- Optional control-plane package:
  - `ael_controlplane/*`

## 4) Communication and boundaries

- Direct Python call chain:
  - `ael` CLI -> pipeline -> runner -> adapter registry -> adapter
- External tool subprocesses:
  - `cmake`, `idf.py`, `arm-none-eabi-gdb`, and related toolchain commands
- Device/API calls:
  - probe/instrument TCP and HTTP(S) endpoints (preflight, LA capture, instrument ops)
- Filesystem outputs:
  - runs under `runs/<run_id>/...` (deterministic default from `ael/paths.py:runs_root`)
  - queue/reports paths under repo root (`ael/paths.py`)

## 5) Core vs optional control-plane split

Core AEL package (`ael/`):

- Contains all functionality required by default CLI (`run`, `pack`, `doctor`, `verify-default`, `instruments`, `dut`).
- Does not depend on `ael_controlplane/` for these commands.

Optional control-plane package (`ael_controlplane/`):

- Depends on core AEL runtime as needed.
- Provides task/queue/API/bridge workflows outside the default core CLI path.

## 6) Notes

- Retry budget precedence is in runner:
  - `step.retry_budget` > `plan.recovery_policy.retries` > built-in defaults.
- Recovery hook exists, but practical recovery actions are still limited.
