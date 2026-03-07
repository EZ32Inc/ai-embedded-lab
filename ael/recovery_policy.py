from __future__ import annotations

from typing import Any, Dict

from ael import failure_recovery


_RECOVERABLE_BY_DEFAULT = {
    failure_recovery.FAILURE_VERIFICATION_MISS: True,
    failure_recovery.FAILURE_TRANSPORT_ERROR: True,
    failure_recovery.FAILURE_VERIFICATION_MISMATCH: False,
    failure_recovery.FAILURE_INSTRUMENT_NOT_READY: False,
    failure_recovery.FAILURE_TIMEOUT: False,
    failure_recovery.FAILURE_NON_RECOVERABLE: False,
    failure_recovery.FAILURE_UNKNOWN: False,
}

_DEFAULT_ACTION_BY_FAILURE = {
    failure_recovery.FAILURE_VERIFICATION_MISS: "reset.serial",
}

_MAX_ATTEMPTS_BY_ACTION = {
    "reset.serial": 1,
    "control.reset.serial": 1,
}


def _normalize_step(step: Dict[str, Any] | Any) -> Dict[str, Any]:
    return dict(step) if isinstance(step, dict) else {}


def _normalize_out(step_out: Dict[str, Any] | Any) -> Dict[str, Any]:
    return dict(step_out) if isinstance(step_out, dict) else {}


def default_recoverable(kind: Any) -> bool:
    normalized = failure_recovery.normalize_failure_kind(kind)
    return bool(_RECOVERABLE_BY_DEFAULT.get(normalized, False))


def resolve_hint(
    step: Dict[str, Any] | Any,
    step_out: Dict[str, Any] | Any,
) -> Dict[str, Any] | None:
    step_d = _normalize_step(step)
    out_d = _normalize_out(step_out)

    raw_hint = out_d.get("recovery_hint")
    hint = failure_recovery.normalize_recovery_hint(raw_hint)
    kind = failure_recovery.normalize_failure_kind(out_d.get("failure_kind"))

    if hint:
        if hint.get("recoverable") is False:
            return None
        return hint

    if not default_recoverable(kind):
        return None

    action = _DEFAULT_ACTION_BY_FAILURE.get(kind)
    if not action:
        return None

    # Narrow default synthesis: current representative UART verify path.
    if str(step_d.get("type", "")).strip() != "check.uart_log":
        return None
    inputs = step_d.get("inputs", {})
    if not isinstance(inputs, dict):
        return None
    cfg = inputs.get("observe_uart_cfg", {})
    if not isinstance(cfg, dict):
        return None
    port = cfg.get("port")
    if not port:
        return None
    params = {"port": port, "baud": cfg.get("baud", 115200)}
    return failure_recovery.make_recovery_hint(
        kind=kind,
        recoverable=True,
        preferred_action=action,
        reason="phase_h_policy_default_for_uart_verification_miss",
        params=params,
    )


def allow_action_attempt(action_type: Any, attempts_by_action: Dict[str, int] | Any) -> bool:
    action = str(action_type or "").strip()
    if not action:
        return False
    aliases = failure_recovery.recovery_action_aliases(action)
    if not aliases:
        aliases = {action}
    attempts = dict(attempts_by_action) if isinstance(attempts_by_action, dict) else {}
    max_allowed = None
    for alias in aliases:
        cap = _MAX_ATTEMPTS_BY_ACTION.get(alias)
        if cap is None:
            continue
        max_allowed = cap if max_allowed is None else min(max_allowed, cap)
    if max_allowed is None:
        return True
    used = 0
    for alias in aliases:
        used = max(used, int(attempts.get(alias, 0)))
    return used < int(max_allowed)
