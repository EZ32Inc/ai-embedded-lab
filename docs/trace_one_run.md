# Trace One Run: RP2040 GPIO Signature

## 1) Selected case

- Case/profile: `rp2040_pico` + `gpio_signature`
- Relevant spec/config files:
  - `tests/plans/gpio_signature.json`
  - `configs/boards/rp2040_pico.yaml`
  - `configs/esp32jtag.yaml`
- Run instance traced: `runs/2026-03-05_10-47-29_rp2040_pico_gpio_signature` (successful, `ok: true`)
- Why chosen:
  - Has complete artifacts (`run_plan.json`, runner result, logs, meta, final result).
  - Uses the standard hardware flow (preflight -> build -> flash -> signal verify).

## 2) Run input

- Command shape used by this run (inferred from `meta.json` + resolved defaults):

```bash
python3 -m ael run --board rp2040_pico --test tests/plans/gpio_signature.json
```

- Probe selection:
  - No explicit probe flag is required because `ael/config_resolver.py` default probe is `configs/esp32jtag.yaml`.
- Test intent from spec:
  - Verify a signal pin (`sig`) with freq/duty constraints over ~1s window.
- Environment assumptions:
  - RP2040 toolchain and `PICO_SDK_PATH` available for CMake build.
  - Probe/network reachable for preflight + LA verify.

## 3) End-to-end call chain

1. Entry point invoked: `ael/__main__.py:main`
   - Parses `run` args; resolves probe path; calls `ael.pipeline.run_cli`.
2. Runtime pipeline started: `ael/pipeline.py:run_pipeline`
   - Loads/merges probe+board+test config; creates run directory and initial artifact files.
3. Run plan assembled: `ael/pipeline.py:run_pipeline`
   - Constructs plan steps: `preflight.probe`, `build.cmake`, `load.gdbmi`, `check.signal_verify`.
4. Plan execution invoked: `ael/runner.py:run_plan`
   - Writes `artifacts/run_plan.json`; executes each step with retry loop.
5. Preflight step: `ael/adapter_registry.py:_PreflightAdapter.execute`
   - Calls `ael/adapters/preflight.py:run`; writes `preflight.json`.
6. Build step: `ael/adapter_registry.py:_BuildAdapter.execute`
   - Calls `ael/adapters/build_cmake.py:run`; produces firmware path.
7. Flash step: `ael/adapter_registry.py:_LoadAdapter.execute`
   - Calls `ael/adapters/flash_bmda_gdbmi.py:run`; writes `flash.json`.
8. Verify step: `ael/adapter_registry.py:_SignalVerifyAdapter.execute`
   - Calls `ael/adapters/observe_gpio_pin.py:run` for capture.
   - Calls `ael/verification/la_verify.py:analyze_capture_bytes` for metrics/judgment.
   - Writes `measure.json`.
9. Runner result written: `ael/runner.py:run_plan`
   - Writes `artifacts/result.json` with per-step outcomes.
10. Final orchestration result written: `ael/pipeline.py:run_pipeline`
   - Copies build artifacts to run artifacts dir.
   - Writes top-level `result.json` and `meta.json`.
   - Returns exit code `0`.

## 4) Artifacts produced during the run

From `runs/2026-03-05_10-47-29_rp2040_pico_gpio_signature/`:

- Core status:
  - `result.json`
  - `meta.json`
  - `config_effective.json`
- Logs:
  - `preflight.log`
  - `build.log`
  - `flash.log`
  - `observe.log`
  - `verify.log` (present but this flow’s verify details are mainly in observe/measure)
  - `observe_uart.log`, `observe_uart_step.log` (created even when UART observe not active)
- Step JSON outputs:
  - `preflight.json`
  - `flash.json`
  - `measure.json`
  - `uart_observe.json`
- Runner artifacts:
  - `artifacts/run_plan.json`
  - `artifacts/result.json`
- Copied firmware artifacts:
  - `artifacts/pico_blink.elf`
  - `artifacts/pico_blink.uf2`
  - `artifacts/pico_blink.bin`

## 5) Observed control points

- Step selection/ordering:
  - `ael/pipeline.py:run_pipeline` builds `plan_steps` from board/test config.
- Build method choice:
  - `ael/pipeline.py:_resolve_builder_kind` -> `build.cmake` for this board.
- Flash method choice:
  - `ael/pipeline.py:run_pipeline` chooses `load.gdbmi` unless board flash method is `idf_esptool`.
- Retry behavior:
  - `ael/runner.py:_retry_budget` + retry loop in `run_plan`.
- Pass/fail judgment:
  - Adapter returns (`ok`, `error_summary`) per step.
  - Signal pass/fail finalized in `_SignalVerifyAdapter` using `la_verify` metrics + limits.
- Final exit code mapping:
  - `ael/pipeline.py:_code_from_failed_step` maps failed step prefix to process exit code.
- Final report composition:
  - `ael/pipeline.py:run_pipeline` writes aggregated `result.json` and `meta.json`.

## 6) Gaps / unclear areas

- Exact user CLI command for this historical run is inferred (not directly logged as a single command line).
- `recovery_policy.retries` exists in plan JSON, but effective retry counts are enforced by runner step-type defaults; coupling is implicit.
- Retry budget precedence is now explicit in runner: `step.retry_budget` > `recovery_policy.retries` > built-in defaults.
- `verify.log` is always part of result metadata even when signal verification primarily uses observe + measure files.
