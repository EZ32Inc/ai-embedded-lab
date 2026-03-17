# UART Role/Backend Cleanup (Prompt 18)

Date: 2026-03-06

## Goal

Apply a minimal compatibility-focused cleanup so UART is treated as a backend transport detail, while outer call sites use a role-first observation API.

## Changes

- Added role-first facade module: `ael/adapters/observe_log.py`
  - `run_serial_log(cfg, raw_log_path)` is the new preferred entrypoint.
  - `run(cfg, raw_log_path)` is a compatibility alias.
- Updated `check.uart_log` adapter call path in `ael/adapter_registry.py`:
  - from `observe_uart_log.run(...)`
  - to `observe_log.run_serial_log(...)`
- Kept `ael/adapters/observe_uart_log.py` intact as the UART backend implementation, preserving existing behavior.
- Added focused facade tests in `tests/test_observe_log_facade.py`.
- Updated recovery coverage patch target in `tests/test_phase_f_recovery_coverage.py`.

## Compatibility

- Runtime behavior remains the same.
- Existing internal/external code that imports `observe_uart_log.run` continues to work.
- New code should prefer `observe_log.run_serial_log`.
