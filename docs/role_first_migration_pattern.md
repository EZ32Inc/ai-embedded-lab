# Role-First Migration Pattern

Date: 2026-03-07

## Why This Pattern Exists

Transport-first naming does not scale well. If top-level concepts are named by UART/USB/Wi-Fi/JTAG, orchestration becomes transport-shaped instead of intent-shaped. AEL should describe what we do first, then how it is transported.

## Core Principle

Prefer:

- role-first top-level concepts
- backend/transport-qualified implementations

Useful role categories in AEL:

- action
- observation
- evaluation
- recovery
- policy/planning

## Migration Pattern (Incremental)

1. Identify the path's true role.
2. Introduce a role-first facade or entry point.
3. Push backend/transport-specific logic lower.
4. Preserve compatibility with alias/shim/wrapper.
5. Migrate callers gradually to the role-first entry.

## Current Validated Examples

### 1) Serial log observation

- Role-first facade added: `ael/adapters/observe_log.py` (`run_serial_log`).
- UART backend kept in place: `ael/adapters/observe_uart_log.py`.
- Caller updated to role-first entry:
  - `ael/adapter_registry.py` (`check.uart_log` path now calls `observe_log.run_serial_log`).

Why it matters: top-level observation call site is role-oriented; UART remains backend detail.

### 2) Serial reset recovery/control

- Backend logic extracted: `ael/adapters/control_reset_serial.py`.
- Registry adapter turned into thin wrapper:
  - `ael/adapter_registry.py` (`_SerialResetRecoveryAdapter` delegates).
- Role-first action key added: `control.reset.serial`.
- Legacy key kept: `reset.serial` (alias compatibility).
- Recovery allow-list alias handling added:
  - `ael/failure_recovery.py`, `ael/runner.py`.

Why it matters: recovery intent is explicit; serial RTS/DTR details are lower-level.

## Naming Guidance

- Name outer APIs by role/capability first.
- Use UART/USB/Wi-Fi/PCIe/JTAG as backend qualifiers.
- Keep evidence organized by observed facts/outcomes, not by transport labels.

## Backward Compatibility Guidance

- Keep legacy entry points when still used.
- Use thin wrappers around new role-first paths.
- Prefer additive migration over broad renames.
- Move callers gradually.

## What Not To Do

- Do not introduce a giant generic Interface class.
- Do not rename the whole repo in one pass.
- Do not force abstraction purity over a working flow.
- Do not move transport concerns back into orchestration-level logic.

## When To Apply This Pattern

- A module is primarily transport-named but serves a clear role.
- A path mixes role and backend concerns in one entry point.
- A new backend is being added to an existing role.

## Suggested Future Use

Apply the same pattern for future cleanup in:

- UART-related control/recovery branches (for example download-mode assistance path)
- USB-backed control/observe paths
- Wi-Fi instrument backends
- browser-backed observation paths

Keep each migration small: one path at a time, with compatibility preserved.
