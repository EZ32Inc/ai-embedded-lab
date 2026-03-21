# AEL Architecture Map

**Date:** 2026-03-21
**Based on:** actual repo inspection

---

## Entry Points

| Command | File | Purpose |
|---|---|---|
| `python -m ael run` | `ael/__main__.py` | Execute a single board/test combination |
| `python -m ael pack` | `ael/__main__.py` | Execute a multi-test pack (JSON sequence) |
| `python -m ael verify-default run` | `ael/__main__.py` | Run the full default regression suite |
| `python -m ael doctor` | `ael/__main__.py` | Diagnose control instrument + board health |
| `python -m ael instruments ...` | `ael/__main__.py` | Inventory, describe, and control instruments |
| `python -m ael inventory ...` | `ael/__main__.py` | Audit test/board/connection metadata |
| `python -m ael status` | `ael/__main__.py` | Unified system + project health overview |

---

## One Run Lifecycle

For `python -m ael run --board B --test T`:

1. **CLI dispatch** — `ael/__main__.py`: parse args, resolve probe path from controller ID
2. **Config load** — `ael/config_resolver.py`: load board YAML, probe YAML, test JSON
3. **Strategy resolution** — `ael/strategy_resolver.py::resolve_run_strategy()`: merge configs, select instrument, normalize wiring
4. **Run directory created** — `ael/run_manager.py`: create `runs/YYYY-MM-DD_HH-MM-SS_BOARD_TEST/` with all artifact paths
5. **Plan built** — `ael/pipeline.py`: assemble ordered list of steps (preflight → build → load → run → check)
6. **Steps executed** — `ael/runner.py::run_plan()`: dispatch each step to its adapter via `AdapterRegistry`
   - **preflight** → `ael/adapters/preflight.py`: TCP-ping endpoints, check bench setup readiness
   - **build** → `ael/adapters/build_{cmake|idf|stm32}.py`: compile firmware, produce ELF
   - **load** → `ael/adapters/flash_{bmda_gdbmi|idf}.py`: flash firmware to target via GDB/esptool
   - **run** → `ael/adapters/observe_{uart_log|gpio_pin}.py`: capture UART or GPIO during execution
   - **check** → `ael/adapters/check_mailbox_verify.py` or signal verification: validate against test expectations
7. **Retry / recovery** — `ael/runner.py`: on failure, consult `recovery_policy.py`, execute recovery action, rewind and retry
8. **Result written** — `runs/.../result.json`, `runs/.../evidence.json`, workflow event archived

---

## Main Components

| Component | File(s) | Role |
|---|---|---|
| CLI / command dispatch | `ael/__main__.py` | Arg parsing; routes to pipeline, instruments, inventory, verify-default |
| Run orchestration | `ael/pipeline.py` | Loads configs, builds plan, calls runner, archives events |
| Plan executor | `ael/runner.py` | Executes steps in order; retry budget; recovery dispatch |
| Adapter registry | `ael/adapter_registry.py` | Maps `step.type` string → adapter instance |
| Strategy resolver | `ael/strategy_resolver.py` | Selects instrument, resolves wiring, builds preflight/build/load/run/check steps |
| Config loader | `ael/config_resolver.py` | Reads board YAML, probe YAML from `configs/` |
| Run artifact manager | `ael/run_manager.py` | Creates timestamped `runs/` directory; provides all log/result paths |
| Connection model | `ael/connection_model.py` | Normalizes bench wiring; computes `SetupReadinessSummary` |
| Connection metadata | `ael/connection_metadata.py` | Schema validation for `bench_setup`, `power_and_boot`, wiring fields |
| Instrument inventory | `ael/inventory.py` | Builds queryable map of boards, tests, connections |
| Instrument health | `ael/instrument_doctor.py`, `ael/doctor_checks.py` | Diagnostic checks for probe + board readiness |
| Default verification | `ael/default_verification.py` | Multi-board parallel suite runner; regression snapshots |
| Failure recovery | `ael/failure_recovery.py`, `ael/recovery_policy.py` | Maps failure kinds → recovery actions |
| Pack loader | `ael/pack_loader.py` | Loads multi-test JSON packs |
| Verification logic | `ael/verification/` | Signal check evaluation, LA capture analysis |
| Build adapters | `ael/adapters/build_*.py` | CMake (RP2040), IDF (ESP32), STM32 Make wrappers |
| Flash adapters | `ael/adapters/flash_*.py` | GDB+BMDA (STM32/RP2040), esptool (ESP32) |
| Observe adapters | `ael/adapters/observe_*.py` | UART log capture, GPIO pin observation |
| Check adapters | `ael/adapters/check_*.py` | Mailbox verify, signal verify |
| Preflight adapter | `ael/adapters/preflight.py` | TCP reachability, bench setup readiness |
| Instrument backends | `instruments/` | ESP32JTAG, ESP32 meter, ST-Link, USB UART drivers |

---

## Communication and Call Relationships

- **Python function calls**: primary path between all CORE modules (pipeline → runner → adapters)
- **JSON files**: test plans in `tests/plans/`, packs in `packs/`, run results in `runs/`
- **YAML files**: board configs in `configs/boards/`, probe configs in `configs/probes/`
- **Subprocess**: build tools (make, cmake, idf.py), flash tools (esptool), GDB sessions (gdb+st-util or gdb+BMDA)
- **HTTP**: instrument backends communicate with physical instruments over HTTP (ESP32 meter, ESP32JTAG REST API)
- **TCP socket**: preflight TCP-pings instrument endpoints; GDB connects to st-util or BMDA GDB server
- **Serial/SWD**: ST-Link and ESP32JTAG bit-bang SWD to flash and debug targets
- **JSONL**: `workflow_archive/events.jsonl` records all run events for audit

---

## Core vs Adapter Split

### Core orchestration (ael_guard protected)

These files must not reference specific board types, MCUs, or external tools by name.

- `ael/__main__.py`
- `ael/pipeline.py`
- `ael/runner.py`
- `ael/run_manager.py`
- `ael/config_resolver.py`
- `ael/doctor_checks.py`
- `ael/strategy_resolver.py`
- `ael/connection_model.py`
- `ael/adapter_registry.py`

### Adapters and board-specific layers

These may freely reference hardware, MCUs, tools, and vendors.

- `ael/adapters/` — all adapter modules
- `instruments/` — ESP32JTAG, ESP32 meter, ST-Link, USB UART backends
- `configs/boards/` — per-board YAML (target, flash method, wiring, power_and_boot)
- `configs/probes/` — per-probe YAML (IP, port, gdb_cmd)
- `firmware/targets/` — per-target firmware source

---

## Immediate Pain Points Noticed

- **`adapter_registry.py` is large**: nominally CORE but contains inline adapter class definitions that reference specific instrument types and step names. The registry is the right place for dispatch, but mixing registration with implementation makes it harder to extend.
- **Strategy resolver doubles as step builder**: `strategy_resolver.py` resolves configs AND builds the preflight/build/load/run/check step dicts. These two concerns are currently intertwined.
- **Retry and recovery are split**: retry budget lives in `runner.py`; recovery actions live in `failure_recovery.py` and `recovery_policy.py`. The rewind/retry interaction requires reading three files to understand.
- **No unified instrument capability registry**: whether a given instrument can do voltage measurement, digital capture, or JTAG depends on runtime dispatch through several layers. There is no single declarative place to query instrument capabilities.
- **Draft board configs contain placeholder values**: `configs/boards/*_draft.yaml` files have literal `PLACEHOLDER` strings that pass YAML load but would fail value-level schema validation.
