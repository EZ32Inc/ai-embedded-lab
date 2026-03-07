# AEL Architecture Principles

## Purpose

These rules keep AEL clear as it grows across boards, instruments, and transports.

## 1. Name top-level concepts by role

Prefer top-level concepts such as:

- action
- observation
- evaluation
- recovery
- policy / planning

These describe **what the system is doing**.

## 2. Keep transport/backend details lower in the stack

Names such as:

- UART
- USB
- Wi-Fi
- PCIe
- JTAG
- SWD
- Socket

should usually appear as:

- backend qualifiers
- transport qualifiers
- adapter names
- source fields

These describe **how the system does something**, not the top-level role.

## 3. Name “what” before “how”

Prefer:

- `reset.serial`
- `observe_log_via_uart`
- `evaluate_signal_facts`

Avoid:

- `uart_reset_module`
- `wifi_checker`
- `usb_verifier_core`

## 4. Separate facts from judgment

As much as practical:

- observation/check code should produce facts
- evaluation code should interpret facts
- evidence should preserve observed facts
- recovery/policy should use evaluated outcomes

## 5. Evidence should be organized by observed fact, not by transport

Prefer evidence kinds like:

- log
- signal
- signature
- measurement
- status

Then record source separately, for example:

- `source = uart`
- `source = logic_analyzer`
- `source = wifi_instrument`

## 6. Recovery names should describe the action first

Prefer:

- `reset.serial`
- `reconnect.instrument`
- `rearm.capture`

Avoid:

- `uart_recovery`
- `wifi_fix`
- `usb_recovery_manager`

## 7. Quick check for new code

Before adding a new module or name, ask:

1. Is this primarily an action, observation, evaluation, recovery, or policy concern?
2. Is the name describing a role, or only a transport?
3. If the backend changed tomorrow, would the high-level name still make sense?

## 8. Short version

- Top level by role
- Lower level by transport/backend
- Name what the system does before naming how it does it
- Keep facts separate from judgment
