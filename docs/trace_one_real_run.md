# Trace One Real Run

## A) Selected Case

- Case: `rp2040_pico` + `tests/plans/rp2040_gpio_signature.json`
- Real run directory: `runs/2026-03-06_17-00-39_rp2040_pico_gpio_signature`
- Why this case:
  - Typical core hardware path (preflight -> build -> flash -> signal verify).
  - Complete artifacts and logs are present.

## B) Run Input

Representative command shape:

```bash
python3 -m ael run --board rp2040_pico --test tests/plans/rp2040_gpio_signature.json
```

Resolved defaults in this run:
- Probe config: `configs/esp32jtag.yaml` (default resolution path)
- Board config: `configs/boards/rp2040_pico.yaml`
- Test config: `tests/plans/rp2040_gpio_signature.json`

Assumptions:
- RP2040 toolchain + `PICO_SDK_PATH` available.
- Probe reachable over network.

## C) End-to-End Call Chain

1. `ael/__main__.py:main`
- Parses `run` CLI and resolves inputs.

2. `ael/pipeline.py:run_cli`
- Thin wrapper forwarding into runtime orchestration.

3. `ael/pipeline.py:run_pipeline`
- Loads configs, creates run directory, builds `runplan/0.1`, prepares step list.

4. `ael/run_manager.py:create_run`
- Allocates run id/path and standard log/json/artifact paths.

5. `ael/runner.py:run_plan`
- Executes plan steps in order with retries.

6. `ael/adapter_registry.py:_PreflightAdapter.execute`
- Calls `ael/adapters/preflight.py:run`.

7. `ael/adapter_registry.py:_BuildAdapter.execute`
- Calls `ael/adapters/build_cmake.py:run` for RP2040 build.

8. `ael/adapter_registry.py:_LoadAdapter.execute`
- Calls `ael/adapters/flash_bmda_gdbmi.py:run` for flash/program.

9. `ael/adapter_registry.py:_SignalVerifyAdapter.execute`
- Calls `ael/adapters/observe_gpio_pin.py:run` and `ael/verification/la_verify.py:analyze_capture_bytes`.

10. `ael/runner.py:run_plan` return -> `ael/pipeline.py:run_pipeline`
- Final pass/fail, writes top-level result/meta, copies firmware artifacts, returns CLI code.

## D) Artifacts Produced

From `runs/2026-03-06_17-00-39_rp2040_pico_gpio_signature/`:

- Top-level status/config:
  - `result.json`, `meta.json`, `config_effective.json`
- Logs:
  - `preflight.log`, `build.log`, `flash.log`, `observe.log`, `verify.log`
  - `observe_uart.log`, `observe_uart_step.log`
- Step JSON outputs:
  - `preflight.json`, `flash.json`, `measure.json`, `uart_observe.json`
- Runner artifacts:
  - `artifacts/run_plan.json`, `artifacts/result.json`, `artifacts/runtime_state.json`
- Copied firmware artifacts:
  - `artifacts/pico_blink.elf`, `artifacts/pico_blink.uf2`, `artifacts/pico_blink.bin`

## E) Control Decision Points

- Board/control-instrument/test resolution:
  - `ael/__main__.py:main`, `ael/config_resolver.py`
- Build/flash/verify step shaping:
  - `ael/pipeline.py:run_pipeline`
- Retry budget and attempts:
  - `ael/runner.py:_retry_budget`, `run_plan`
- Adapter selection:
  - `ael/adapter_registry.py:AdapterRegistry.get`
- Pass/fail result and failed step mapping:
  - `ael/runner.py:run_plan`, `ael/pipeline.py:_code_from_failed_step`
- Result/meta writing:
  - `ael/pipeline.py:run_pipeline`

## F) Unclear or Fragile Areas

- Exact historical CLI command for a past run is inferred from artifacts, not stored verbatim.
- Strategy branching is split across pipeline and adapter registry, so flow tracing requires reading both.
- Recovery path is present but limited by current noop recovery implementation.
