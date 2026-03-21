# Trace One Real Run

**Date:** 2026-03-21
**Based on:** actual run artifacts from `runs/2026-03-21_13-41-22_stm32f411ceu6_stm32f411_gpio_signature/`

---

## 1. Selected Case

**Case:** `stm32f411_gpio_signature`
**Board:** `stm32f411ceu6` (STM32F411CEU6 WeAct Black Pill V2.0)
**Instrument:** `esp32jtag_stm32f411` @ 192.168.2.103 (ESP32JTAG over WiFi)

**Config files:**
- Board: `configs/boards/stm32f411ceu6.yaml`
- Probe: `configs/probes/esp32jtag_stm32f411.yaml` (resolved from instrument_instance)
- Test plan: `tests/plans/stm32f411_gpio_signature.json`

**Why this case:** Exercises the full pipeline — ARM build → SWD flash via GDB/BMDA → logic analyzer capture → signal frequency/ratio check. Representative of the STM32 + ESP32JTAG path, which covers the majority of bench targets.

---

## 2. Run Input

```bash
python -m ael run \
  --board stm32f411ceu6 \
  --test tests/plans/stm32f411_gpio_signature.json \
  --controller esp32jtag_stm32f411
```

Or equivalently, invoked as one worker inside `python -m ael verify-default run`.

**Test plan summary (`stm32f411_gpio_signature.json`):**
- Two signal checks: `pa2_fast` (150–400 Hz), `pa3_half_rate` (75–200 Hz)
- One relation check: frequency ratio PA2/PA3 must be 1.8–2.2×
- `bench_setup.peripheral_signals`: declares PA2, PA3, PC13 as DUT outputs

---

## 3. End-to-End Call Chain

1. **`ael/__main__.py:main()`** — parses args, resolves `--controller` → probe YAML path via `config_resolver.resolve_control_instrument_instance()`

2. **`ael/pipeline.py:run_pipeline()`** — top-level orchestrator:
   - calls `config_resolver` to load board YAML, probe YAML, test JSON
   - calls `strategy_resolver.resolve_run_strategy()` to merge all three into a `ResolvedRunStrategy`

3. **`ael/strategy_resolver.py:resolve_run_strategy()`**:
   - resolves instrument: reads `board.instrument_instance` → looks up `esp32jtag_stm32f411` in `configs/probes/`
   - normalizes connection context via `connection_model.normalize_connection_context()`: wiring = `swd=P3, reset=NC, verify=P0.0`
   - computes `SetupReadinessSummary` for bench_setup peripheral signals
   - builds step dicts: preflight, build, load, check_signal

4. **`ael/run_manager.py:create_run()`** — creates `runs/2026-03-21_13-41-22_stm32f411ceu6_stm32f411_gpio_signature/` with all sub-paths

5. **`ael/pipeline.py`** — writes `artifacts/run_plan.json` (4 steps: preflight, build, load, check_signal)

6. **`ael/runner.py:run_plan()`** — dispatches steps in sequence:

   **Step 1 — `preflight` (`preflight.probe`)**
   → `adapter_registry._PreflightAdapter.execute()`
   → `ael/adapters/preflight.py:run(probe_cfg)`: ping 192.168.2.103, TCP check :4242, monitor targets, LA self-test
   → Result: ok=True; writes `preflight.json`, `preflight.log`

   **Step 2 — `build` (`build.arm_debug`)**
   → `adapter_registry._BuildAdapter.execute()`
   → `ael/adapters/build_stm32.py`: runs `make` in `firmware/targets/stm32f411ceu6/`
   → Produces `stm32f411_app.elf`, `stm32f411_app.bin` → copied to `artifacts/`
   → Result: ok=True; writes `build.log`

   **Step 3 — `load` (`load.gdbmi`)**
   → `adapter_registry._LoadAdapter.execute()`
   → `ael/adapters/flash_bmda_gdbmi.py`: starts/reuses st-util or BMDA GDB server at :4242, launches GDB session with `gdb_launch_cmds` (monitor a → attach → load → detach)
   → Result: ok=True; writes `flash.log`, `flash.json`

   **Step 4 — `check_signal` (`check.signal_verify`)**
   → `adapter_registry._SignalVerifyAdapter.execute()`
   → calls instrument HTTP API at `https://192.168.2.103:443` to configure LA and capture PA2 (P0.0) and PA3 (P0.1)
   → `ael/check_eval.py`: evaluates frequency, duty cycle, edge counts against test plan thresholds
   → evaluates frequency ratio PA2/PA3 (must be 1.8–2.2×)
   → Result: ok=True; writes `verify.log`, `measure.json`

7. **`ael/runner.py`** — returns `{"ok": true, "termination": "pass", "retry_summary": {"step_attempts": 4, "recovery_attempts": 0}}`

8. **`ael/pipeline.py`** — writes `result.json`, archives workflow event to `workflow_archive/events.jsonl`

---

## 4. Artifacts Produced

| File | Contents |
|---|---|
| `artifacts/run_plan.json` | Full 4-step execution plan with all inputs |
| `artifacts/result.json` | Step-level results (name, type, ok per step) |
| `artifacts/stm32f411_app.elf` | Compiled firmware ELF |
| `artifacts/stm32f411_app.bin` | Compiled firmware binary |
| `build.log` | make stdout/stderr |
| `flash.log` | GDB session log (monitor a, attach, load, detach) |
| `flash.json` | Flash strategy metadata (speed_khz, target_id, attempts) |
| `preflight.log` | Ping, TCP, monitor targets, LA self-test output |
| `preflight.json` | Structured preflight result (ping_ok, tcp_ok, monitor_ok, la_ok) |
| `verify.log` | LA capture details, edge counts per channel |
| `measure.json` | Structured instrument measurements (freq_hz, duty, edges per signal) |
| `observe.log` | Raw observation log (empty for this test — no UART) |
| `observe_uart.log` | UART capture (empty for this test) |
| `result.json` | Top-level result (ok, termination, stage_execution, retry_summary, artifacts list) |
| `meta.json` | Run metadata (run_id, board, test, started_at, timeout_s) |
| `config_effective.json` | Merged probe + board + test config snapshot |
| `workflow_events.jsonl` | Per-run event log |

---

## 5. Observed Control Points

| Decision | Where it happens |
|---|---|
| Which instrument to use | `strategy_resolver.py`: reads `board.instrument_instance`, looks up probe YAML |
| Which build type (cmake/idf/arm_debug) | `strategy_resolver.py`: reads `board.build.type` |
| Which flash method (gdbmi/esptool) | `strategy_resolver.py`: reads `board.flash.method` (arm_debug → gdbmi) |
| Which check adapter to use | `strategy_resolver.py`: test plan has `signal_checks` → emits `check.signal_verify` step |
| Retry budget per step | `runner.py`: hardcoded per step type (build=1, load=2, check=2) |
| Recovery action selection | `recovery_policy.py`: maps failure kind (e.g. `flash_failed`) → recovery action |
| Pass/fail judgment per signal check | `check_eval.py`: compares captured freq/duty/edges against test plan thresholds |
| Overall pass/fail | `runner.py`: `termination = "pass"` iff all steps ok=True |
| Result persistence | `pipeline.py`: writes `result.json` after `runner.run_plan()` returns |

---

## 6. Gaps and Unclear Areas

- **Step timing**: `artifacts/result.json` stores step `ok` but not per-step elapsed time. Elapsed time is only tracked at the top-level run (via `started_at`/`ended_at` in `result.json`), not per step.
- **No UART/observe step in this run**: the `stm32f411_gpio_signature` test uses only signal_verify (LA capture via instrument HTTP API), not UART. The `observe_uart_log` adapter path is not exercised here — a mailbox or UART test would show that path.
- **LA capture is implicit in check_signal**: there is no separate `run.gpio_observation` step in this plan. Capture and evaluation are both done inside `_SignalVerifyAdapter`, which calls the instrument backend directly. The boundary between "observe" and "check" is blurred in the signal path.
- **Retry rewind anchor**: `runner.py` supports rewinding to a retry anchor point (e.g., retry from `load` after a flash failure), but the anchor assignment logic is embedded in the step plan and not visible in the result artifacts.
- **Recovery path not exercised here**: `retry_summary.recovery_attempts = 0`. The recovery dispatch path (failure_recovery → recovery_policy → recovery adapter) requires a failing run to observe.
