# Serial Role/Backend Cleanup (Prompt 19)

Date: 2026-03-06

## 1) Chosen path

Chosen path: recovery action for serial RTS reset, previously keyed only as `reset.serial` and implemented directly in `ael/adapter_registry.py`.

## 2) True role

This path is a recovery/control action: reset target control during failure recovery. Serial/UART is only the transport backend.

## 3) What changed

- Introduced backend module `ael/adapters/control_reset_serial.py` with `run(params, action_type=...)`.
- Kept registry-facing recovery adapter, but made it a thin wrapper that delegates to `control_reset_serial.run(...)`.
- Added role-first recovery action key `control.reset.serial`.
- Kept legacy action key `reset.serial` as compatibility alias.
- Runner recovery allow-list matching now treats `reset.serial` and `control.reset.serial` as equivalent aliases.

## 4) What remains serial/UART-specific

These backend details stay in `control_reset_serial`:

- pyserial import/usage
- serial port and baud parameters
- RTS/DTR pulse sequencing
- pulse/settle timing and serial open/close error handling

## 5) Backward compatibility

- Existing plans/hints/policies using `reset.serial` continue working.
- Registry still accepts `reset.serial`.
- New role-first `control.reset.serial` also works.
- Legacy error text is preserved when invoked as `reset.serial`.

## 6) Known limitations

- Other serial/UART-related paths still use transport-first naming in parts of the codebase.
- Recovery hint producers still mostly emit `reset.serial`; this change only adds role-first compatibility and one representative cleanup path.
