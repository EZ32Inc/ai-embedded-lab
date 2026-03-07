from __future__ import annotations

from typing import Any, Dict

RECOVERY_ACTION_RESET_SERIAL = "reset.serial"
RECOVERY_ACTION_CONTROL_RESET_SERIAL = "control.reset.serial"


FAILURE_VERIFICATION_MISS = "verification_miss"
FAILURE_VERIFICATION_MISMATCH = "verification_mismatch"
FAILURE_INSTRUMENT_NOT_READY = "instrument_not_ready"
FAILURE_TRANSPORT_ERROR = "transport_error"
FAILURE_TIMEOUT = "timeout"
FAILURE_NON_RECOVERABLE = "non_recoverable"
FAILURE_UNKNOWN = "unknown"

KNOWN_FAILURE_KINDS = {
    FAILURE_VERIFICATION_MISS,
    FAILURE_VERIFICATION_MISMATCH,
    FAILURE_INSTRUMENT_NOT_READY,
    FAILURE_TRANSPORT_ERROR,
    FAILURE_TIMEOUT,
    FAILURE_NON_RECOVERABLE,
    FAILURE_UNKNOWN,
}

_RECOVERY_ACTION_ALIASES = {
    RECOVERY_ACTION_RESET_SERIAL: {RECOVERY_ACTION_RESET_SERIAL, RECOVERY_ACTION_CONTROL_RESET_SERIAL},
    RECOVERY_ACTION_CONTROL_RESET_SERIAL: {RECOVERY_ACTION_RESET_SERIAL, RECOVERY_ACTION_CONTROL_RESET_SERIAL},
}


def recovery_action_aliases(action_type: Any) -> set[str]:
    key = str(action_type or "").strip()
    if not key:
        return set()
    return set(_RECOVERY_ACTION_ALIASES.get(key, {key}))


def normalize_failure_kind(kind: Any) -> str:
    k = str(kind or "").strip().lower()
    return k if k in KNOWN_FAILURE_KINDS else FAILURE_UNKNOWN


def make_recovery_hint(
    *,
    kind: Any,
    recoverable: bool,
    preferred_action: str,
    reason: str,
    scope: str = "step",
    retry: bool = True,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "kind": normalize_failure_kind(kind),
        "recoverable": bool(recoverable),
        "preferred_action": str(preferred_action or "").strip(),
        "reason": str(reason or "").strip(),
        "scope": str(scope or "step").strip(),
        "retry": bool(retry),
        "params": dict(params or {}),
        # Backward-compat field for existing runner path.
        "action_type": str(preferred_action or "").strip(),
    }


def normalize_recovery_hint(raw: Dict[str, Any] | Any) -> Dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = normalize_failure_kind(raw.get("kind"))
    preferred_action = str(raw.get("preferred_action") or raw.get("action_type") or "").strip()
    if not preferred_action:
        return None
    return {
        "kind": kind,
        "recoverable": bool(raw.get("recoverable", True)),
        "preferred_action": preferred_action,
        "reason": str(raw.get("reason") or "").strip(),
        "scope": str(raw.get("scope") or "step").strip(),
        "retry": bool(raw.get("retry", True)),
        "params": dict(raw.get("params", {})) if isinstance(raw.get("params"), dict) else {},
        "action_type": preferred_action,
    }
