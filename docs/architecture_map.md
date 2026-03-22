# AEL Architecture Map

**Date:** 2026-03-22
**Status:** Current (based on live codebase)

---

## 1. Entry Points

| Entry point | File | Key function/class | Purpose |
|---|---|---|---|
| CLI main | `ael/__main__.py` | `main()` | Argparse router for all subcommands |
| Single test run | `ael/pipeline.py` | `run_pipeline()` | Full pipeline: config → build → flash → observe → report |
| Verification suite | `ael/default_verification.py` | `run_default_setting()` | Parallel multi-board test suite with health governance |
| Stage explain | `ael/stage_explain.py` | `explain_stage()` | Structured metadata/plan view for a given stage |
| Doctor | `ael/instrument_doctor.py` | `run_doctor()` | Instrument + connection health diagnostics |

**CLI subcommands:** `run`, `doctor`, `pack`, `instruments`, `dut`, `verify-default`, `inventory`, `connection`, `explain-stage`, `workflow-archive`, `hw-check`, `la-check`, `status`, `board`, `project`

---

## 2. One Run Lifecycle

```
CLI  →  pipeline.run_pipeline()
          │
          ├─ 1. Config merge      config_resolver, pipeline._merge_configs()
          │                        board.yaml + probe.yaml + test.json → effective config
          │
          ├─ 2. Strategy resolve  strategy_resolver.resolve_run_strategy()
          │                        selects build/flash/observe method; Phase 1 compatibility check
          │
          ├─ 3. Plan build        pipeline._build_plan()
          │                        ordered list of Step objects (preflight, build, load, run, check)
          │
          ├─ 4. Preflight         adapters/preflight.py
          │                        ping, TCP reachability, probe monitor, instrument health
          │
          ├─ 5. Build             adapters/build_cmake.py | build_idf.py | build_stm32.py
          │                        firmware compiled for target board
          │
          ├─ 6. Flash             adapters/flash_bmda_gdbmi.py | flash_idf.py
          │                        binary loaded to DUT via SWD/GDB-MI or IDF esptool
          │
          ├─ 7. Observe / Run     adapters/observe_gpio_pin.py | observe_uart_log.py | observe_log.py
          │                        GPIO edge capture (via instrument), UART frame capture
          │
          ├─ 8. Verify            adapters/check_mailbox_verify.py | verification/la_verify.py
          │                        mailbox result check, logic analyzer edge verification
          │
          └─ 9. Report            pipeline._build_validation_summary()
                                   result JSON + console output; evidence.json artifact
```

**Retry / recovery:** `runner.run_plan()` implements a per-step retry budget. On failure, `failure_recovery.py` normalises the failure kind and `recovery_policy.py` resolves recovery hints (e.g. replug, reset, reflash).

---

## 3. Main Components

### Orchestration (Core)

| Module | Purpose |
|---|---|
| `pipeline.py` (~2100 lines) | Master orchestrator: config merge, plan building, stage loop, summary |
| `runner.py` | Step execution engine: retry loop, timeout, failure classification |
| `strategy_resolver.py` | Build/load/run strategy selection; Phase 1 instrument compatibility |
| `adapter_registry.py` | String-keyed router: step type → adapter callable |
| `config_resolver.py` | CLI default resolution, board/probe config discovery |
| `run_manager.py` | Run directory lifecycle, `Tee` output buffering |
| `default_verification.py` | Verification suite: parallel workers, health inference, regression snapshot |
| `connection_model.py` | Wiring digest, connection setup validation, readiness checks |

### Compatibility Layer

| Module | Purpose |
|---|---|
| `compatibility/resolver.py` | Phase 1–3 resolvers: test↔instrument, DUT↔test, DUT↔instrument |
| `compatibility/registry.py` | Surface key → capability type mappings; DUT feature → required surfaces |
| `compatibility/model.py` | Result dataclasses: `CompatibilityResult`, `ExecutionPlan`, `DUTSpec`, etc. |
| `compatibility/rules.py` | Requirement matching logic |
| `compatibility/explain.py` | Human-readable compatibility explanations |

### DUT Layer

| Module | Purpose |
|---|---|
| `dut/model.py` | `DUTConfig` dataclass: board identity, processor, kind, features |
| `dut/loader.py` | YAML → `DUTConfig` deserialization |
| `dut/registry.py` | DUT catalog lookup by board ID |

### Instrument Layer

| Module | Purpose |
|---|---|
| `instruments/registry.py` | Instrument catalog; `find_by_capability()` |
| `instruments/dispatcher.py` | Action dispatcher: validates and routes to backend |
| `instruments/action_registry.py` | `ACTION_REGISTRY`: known actions, schemas |
| `instruments/manifest.py` | Manifest loading/parsing |
| `instruments/native_api_dispatch.py` | Native API invocation bridge |
| `instruments/backends/esp32_jtag/` | ESP32-JTAG driver (SWD bit-bang, GPIO, reset) |
| `instruments/backends/esp32_meter/` | ESP32 meter driver (voltage, GPIO measurement) |
| `instruments/backends/stlink/` | ST-Link driver (SWD flash, doctor) |
| `instruments/backends/usb_uart_bridge/` | UART bridge daemon |

### Adapters (Step Executors)

| Adapter | Step type |
|---|---|
| `adapters/build_cmake.py` | `build.cmake` |
| `adapters/build_idf.py` | `build.idf` |
| `adapters/flash_bmda_gdbmi.py` | `load.swd` (SWD via BMDA/GDB-MI) |
| `adapters/flash_idf.py` | `load.idf` (ESP32 esptool) |
| `adapters/preflight.py` | `preflight` |
| `adapters/observe_gpio_pin.py` | `run.gpio_signature` |
| `adapters/observe_uart_log.py` | `run.uart_log` |
| `adapters/check_mailbox_verify.py` | `check.mailbox` |
| `adapters/control_reset_serial.py` | `control.reset` |

### Supporting Modules

| Module | Purpose |
|---|---|
| `inventory.py` | DUT/bench resource summaries, connection queries |
| `evidence.py` | Structured observation records (JSON schema) |
| `failure_recovery.py` | Failure kind normalisation |
| `recovery_policy.py` | Recovery hint lookup table |
| `connection_doctor.py` | Connection health checks |
| `instrument_doctor.py` | Instrument diagnostics |
| `verify_default_snapshot.py` | Regression snapshot comparison |
| `workflow_archive.py` | Event logging (JSONL) |
| `test_plan_schema.py` | Test metadata extraction helpers |

---

## 4. Communication / Call Relationships

- **Direct Python calls** — primary pattern throughout: CLI → pipeline → runner → adapters
- **Subprocess** — build (`cmake`, `make`, `idf.py`), flash (`gdb` + GDB-MI, `stm32cubeprogrammer`)
- **JSON/YAML files** — board YAML, probe YAML, test JSON merged into effective config; result JSON per run; `evidence.json` artifact
- **HTTP REST** — remote instrument APIs (esp32_meter meter API, LA web API)
- **TCP** — probe GDB server (`host:4242`), ESP32-JTAG endpoint
- **Serial (pyserial)** — UART capture, ESP32 download mode control
- **SWD / JTAG** — via BMDA/GDB-MI over TCP to probe
- **File-based state** — run directory (`runs/{id}/`) holds logs per stage, effective config, result JSON

---

## 5. Core vs Adapter Split

**Core orchestration** — logic that is not specific to any board or tool:

```
pipeline.py          runner.py           strategy_resolver.py
adapter_registry.py  config_resolver.py  run_manager.py
default_verification.py                  compatibility/
connection_model.py  failure_recovery.py recovery_policy.py
dut/                 run_contract.py     gates.py
```

**Adapters / board-specific / tool-specific:**

```
adapters/build_*.py          adapters/flash_*.py
adapters/observe_*.py        adapters/check_*.py
adapters/preflight.py        adapters/control_*.py
adapters/instrument_*.py
instruments/backends/esp32_jtag/
instruments/backends/esp32_meter/
instruments/backends/stlink/
instruments/backends/usb_uart_bridge/
configs/boards/*.yaml        configs/*.yaml
firmware/targets/*/          tests/plans/*.json
```

---

## 6. Immediate Pain Points Noticed

1. **`pipeline.py` is too large (~2100 lines)** — config merging, plan building, stage routing, summary formatting, and debug rendering all in one file. Candidates to split out: `config_merger`, `plan_builder`, `run_orchestrator`, `summary_formatter`.

2. **`runner.run_plan()` is long (~400+ lines)** — retry loop, recovery dispatch, timeout handling, and failure classification all mixed together. Hard to trace control flow.

3. **Config loading has no single entry point** — board from `configs/boards/{id}.yaml`, probe from `configs/{id}.yaml`, test from `tests/plans/{id}.json`, instrument instances from `configs/instrument_instances/{id}.yaml`. Merging is scattered across `pipeline.py` and `config_resolver.py`.

4. **Connection model is split across four modules** — `connection_model.py`, `connection_metadata.py`, `connection_doctor.py`, `adapters/preflight.py`. No single source of truth for connection readiness.

5. **Instrument layer has dual abstraction** — old manifest-based `registry.py` / `manifest.py` path alongside newer action dispatcher (`dispatcher.py`, `action_registry.py`). Both active; some backends reachable from both paths.

6. **Step types are plain strings** — `adapter_registry.get("build.cmake")` style. No compile-time discovery or validation of which step types exist.

7. **Evidence vs result are separate schemas** — `artifacts/evidence.json` and `runs/{id}/result.json` use different structures with no explicit link between them.
