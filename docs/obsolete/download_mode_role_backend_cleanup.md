# Download-Mode Role/Backend Cleanup

Date: 2026-03-07

## 1) Path Cleaned Up

Cleaned path: download-mode UART assistance branch in `ael/adapters/observe_uart_log.py`, where download-mode detection could trigger an RTS-based reset assist.

## 2) Mixed Roles Before

Before cleanup, this branch mixed:

- observation (UART capture/log scan)
- evaluation (download-mode detection)
- control/recovery action (RTS reset pulse)
- transport details (pyserial open/toggle/close)

inside the same observation module path.

## 3) What Changed

- Added role-first control helper:
  - `ael/adapters/control_download_mode_serial.py`
  - entry: `assist_exit_download_mode(...)`
  - action identity: `control.download_mode.serial_assist`
- Refactored `observe_uart_log` local reset helper to delegate to that control helper.
- Reused existing serial reset backend implementation via:
  - `ael/adapters/control_reset_serial.py` (now supports optional `serial_mod` injection for adapter-level reuse/testing).

Observation and detection remain in the observation path; control action is now explicit and delegated.

## 4) What Remains Serial/UART-Specific

Serial/UART details remain at backend layer:

- pyserial object usage
- serial port/baud configuration
- RTS/DTR pulse timings
- transport open/close behavior

## 5) Backward Compatibility

- Main observation flow and return payload behavior remain unchanged.
- Existing `_try_esp32_rts_reset(...)` helper still exists as a compatibility wrapper and keeps legacy `(ok, message)` shape.
- No changes required to existing callers/config defaults.

## 6) Why This Is a Useful Third Migration Example

It complements:

- role-first observation cleanup (`observe_log` facade),
- role-first reset recovery cleanup (`control.reset.serial` alias path),

by covering a mixed boundary where observation/evaluation triggers control assistance.

## 7) Known Limitations

- Download-mode logic still lives near observation flow decision points.
- Broader transport-neutral policy orchestration is intentionally out of scope for this small cleanup.
