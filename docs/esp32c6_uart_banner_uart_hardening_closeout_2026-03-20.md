# ESP32-C6 UART Banner UART Hardening Closeout

Date: 2026-03-20

## Scope

This change hardens the UART-observe path used by `esp32c6_uart_banner` and similar tests that declare a serial console in `bench_setup.serial_console`.

The immediate trigger was a flaky failure pattern in `esp32c6_uart_banner`:

- flash succeeded
- instrument signature checks were otherwise healthy
- UART observe sometimes captured `0 bytes / 0 lines`
- the expected banner `AEL_READY ESP32C6 UART` was therefore missed

## Root Cause Observed

The failing and passing banner runs showed an important implementation detail:

- `bench_setup.serial_console.port` existed in effective metadata as `auto_usb_serial_jtag`
- but `build_uart_step()` did not propagate that serial-console declaration into `observe_uart_cfg`
- `check_uart` therefore depended entirely on `flash.json.port` fallback

That fallback was often enough to pass, but it left the UART path under-specified and more fragile than it needed to be.

## Change Made

Two low-risk changes were made.

### 1. `build_uart_step()` now carries serial-console metadata into UART observe config

File:
- `ael/strategy_resolver.py`

Behavior:
- if `observe_uart.port` is unset and `bench_setup.serial_console.port` exists, the UART step now receives that value
- if `observe_uart.baud` is unset and `bench_setup.serial_console.baud` exists, the UART step now receives that value

### 2. `check_uart` now resolves symbolic serial-console ports through flash results

File:
- `ael/adapter_registry.py`

Behavior:
- if `observe_uart_cfg.port` is empty, existing `flash.json.port` fallback still applies
- if `observe_uart_cfg.port` is symbolic, such as `auto_usb_serial_jtag`, and `flash.json.port` contains a concrete device path, the adapter now replaces the symbolic value with the concrete flash port before capture

This preserves the existing successful path while making the UART step more explicit and less dependent on accidental propagation.

## Tests Added

### Strategy assembly coverage

File:
- `tests/test_strategy_resolver.py`

Added coverage for:
- using `bench_setup.serial_console.port` when `observe_uart.port` is unset
- carrying `bench_setup.serial_console.baud` into UART observe config

### Adapter resolution coverage

File:
- `tests/test_phase_f_recovery_coverage.py`

Added coverage for:
- resolving `auto_usb_serial_jtag` to `/dev/ttyACM0` via `flash.json.port` inside `check_uart`

## Regression Result

Focused and broader regressions passed:

```bash
PYTHONPATH=. pytest -q tests/test_default_verification.py tests/test_strategy_resolver.py tests/test_phase_f_recovery_coverage.py
```

Result:
- `75 passed`

## Live Validation

Representative live rerun after the patch:

- run: `runs/2026-03-20_05-45-02_esp32c6_devkit_esp32c6_uart_banner`
- result: `PASS`
- key checks passed: `uart.verify`, `instrument.signature`

This does not prove the path is permanently non-flaky, but it does prove the hardening patch preserves the successful execution path in real hardware.

## Current Status

Current interpretation:

- this patch improves the UART observe contract for banner-style tests
- it removes an under-specified gap between `serial_console` metadata and `check_uart`
- it likely reduces one source of UART flake
- it does not yet prove that all banner flakiness is eliminated

## Recommended Follow-up

1. Keep treating `esp32c6_uart_banner` as a path worth occasional repeat validation.
2. If flakiness persists, next likely areas are capture timing and post-flash USB-Serial/JTAG settle behavior.
3. Reuse this same hardening pattern for future tests that declare `bench_setup.serial_console` but leave `observe_uart.port` unset.
