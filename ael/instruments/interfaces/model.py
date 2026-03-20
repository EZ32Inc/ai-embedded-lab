from __future__ import annotations

from typing import Any, Callable, Dict, Optional


CONTRACT_VERSION = "instrument_action/v1"
CAPABILITY_TAXONOMY_VERSION = "instrument_capabilities/v1"
STATUS_MODEL_VERSION = "instrument_status/v1"
DOCTOR_MODEL_VERSION = "instrument_doctor/v1"

CAPABILITY_TAXONOMY_KEYS = frozenset({
    "capture.digital",
    "debug.attach",
    "debug.flash",
    "debug.halt",
    "debug.memory_read",
    "debug.reset",
    "measure.digital",
    "measure.voltage",
    "probe.preflight",
    "stim.digital",
    "uart.observe",
    "uart.read",
    "uart.session",
    "uart.write",
})


def enforce_capability_taxonomy(capabilities: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for key, value in (capabilities or {}).items():
        name = str(key).strip()
        if not name:
            continue
        if name not in CAPABILITY_TAXONOMY_KEYS:
            raise ValueError(f"unknown capability taxonomy key: {name}")
        normalized[name] = dict(value or {})
    return normalized


def _fallback_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict) or not payload:
        return None
    return dict(payload)


def _states_from_checks(checks: Dict[str, Any]) -> list[bool | None]:
    states: list[bool | None] = []
    for detail in checks.values():
        if not isinstance(detail, dict):
            continue
        if "ok" not in detail:
            continue
        ok = detail.get("ok")
        if ok is None or isinstance(ok, bool):
            states.append(ok)
    return states


def derive_status_health(*, reachable: Optional[bool], health_domains: Dict[str, Any]) -> str:
    states = _states_from_checks(health_domains)
    concrete = [state for state in states if isinstance(state, bool)]
    if reachable is False and not any(state is True for state in concrete):
        return "offline"
    if concrete and all(state is True for state in concrete):
        return "ready"
    if any(state is False for state in concrete):
        return "degraded" if any(state is True for state in concrete) or reachable else "offline"
    if reachable is True:
        return "degraded" if states else "ready"
    return "unknown"


def derive_doctor_health(*, reachable: Optional[bool], checks: Dict[str, Any]) -> str:
    states = _states_from_checks(checks)
    concrete = [state for state in states if isinstance(state, bool)]
    if concrete and all(state is True for state in concrete) and reachable is not False:
        return "healthy"
    if any(state is False for state in concrete):
        return "degraded" if any(state is True for state in concrete) else "failed"
    if reachable is False:
        return "failed"
    if reachable is True:
        return "degraded" if states else "healthy"
    return "unknown"


def normalize_capabilities_result(
    *,
    family: str,
    capabilities: Dict[str, Dict[str, Any]],
    lifecycle_boundary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    capabilities = enforce_capability_taxonomy(capabilities)
    capability_keys = sorted(capabilities)
    supported_actions = sorted(
        {
            str(action)
            for entry in capabilities.values()
            if isinstance(entry, dict)
            for action in (entry.get("actions") or [])
            if str(action).strip()
        }
    )
    surfaces = sorted(
        {
            str(surface)
            for entry in capabilities.values()
            if isinstance(entry, dict)
            for surface in (entry.get("surfaces") or [])
            if str(surface).strip()
        }
    )
    result: Dict[str, Any] = {
        "instrument_family": family,
        "capability_taxonomy_version": CAPABILITY_TAXONOMY_VERSION,
        "capability_taxonomy_enforced": True,
        "capability_keys": capability_keys,
        "capabilities": capabilities,
        "supported_actions": supported_actions,
        "surfaces": surfaces,
    }
    if lifecycle_boundary:
        result["lifecycle_boundary"] = dict(lifecycle_boundary)
    return result


def normalize_status_result(
    *,
    family: str,
    reachable: Optional[bool],
    health_domains: Dict[str, Any],
    endpoints: Optional[Dict[str, Any]] = None,
    observations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "instrument_family": family,
        "status_model_version": STATUS_MODEL_VERSION,
        "reachable": reachable,
        "health": derive_status_health(reachable=reachable, health_domains=health_domains),
        "health_domains": dict(health_domains or {}),
    }
    if endpoints:
        result["endpoints"] = dict(endpoints)
    if observations:
        result["observations"] = dict(observations)
    return result


def normalize_doctor_result(
    *,
    family: str,
    reachable: Optional[bool],
    checks: Dict[str, Any],
    lifecycle_boundary: Optional[Dict[str, Any]] = None,
    recovery_hint: Optional[str] = None,
    failure_boundary: Optional[str] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "instrument_family": family,
        "doctor_model_version": DOCTOR_MODEL_VERSION,
        "reachable": reachable,
        "health": derive_doctor_health(reachable=reachable, checks=checks),
        "checks": dict(checks or {}),
    }
    if lifecycle_boundary:
        result["lifecycle_boundary"] = dict(lifecycle_boundary)
    if recovery_hint:
        result["recovery_hint"] = str(recovery_hint)
    if failure_boundary:
        result["failure_boundary"] = str(failure_boundary)
    return result


def action_success(
    *,
    family: str,
    action: str,
    requested: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    warnings: Optional[list[str]] = None,
    fallback: Optional[Dict[str, Any]] = None,
    partial: bool = False,
    legacy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "outcome": "partial" if partial else "success",
        "family": family,
        "action": action,
        "requested": dict(requested or {}),
        "result": dict(result or {}),
        "fallback": _fallback_payload(fallback),
        "status": "ok",
        "data": dict(result or {}),
    }
    if warnings:
        payload["warnings"] = [str(item) for item in warnings if str(item).strip()]
    if legacy:
        payload["legacy"] = dict(legacy)
    return payload


def action_failure(
    *,
    family: str,
    action: str,
    code: str,
    message: str,
    retryable: bool = False,
    requested: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    failure_boundary: Optional[str] = None,
    fallback: Optional[Dict[str, Any]] = None,
    unsupported: bool = False,
    legacy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    error: Dict[str, Any] = {
        "code": str(code),
        "message": str(message),
        "retryable": bool(retryable),
    }
    if failure_boundary:
        error["boundary"] = str(failure_boundary)
    if details:
        error["details"] = dict(details)
    payload: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "ok": False,
        "outcome": "unsupported" if unsupported else "failure",
        "family": family,
        "action": action,
        "requested": dict(requested or {}),
        "result": {},
        "error": error,
        "fallback": _fallback_payload(fallback),
        "status": "error",
        "data": {},
    }
    if legacy:
        payload["legacy"] = dict(legacy)
    return payload


def action_unsupported(
    *,
    family: str,
    action: str,
    requested: Optional[Dict[str, Any]] = None,
    supported_actions: Optional[list[str]] = None,
    fallback: Optional[Dict[str, Any]] = None,
    legacy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    if supported_actions:
        details["supported_actions"] = [str(item) for item in supported_actions if str(item).strip()]
    return action_failure(
        family=family,
        action=action,
        code="unsupported_action",
        message=f"unsupported action: {action}",
        retryable=False,
        requested=requested,
        details=details or None,
        failure_boundary="interface_contract",
        fallback=fallback,
        unsupported=True,
        legacy=legacy,
    )


def wrap_legacy_action(
    legacy_payload: Dict[str, Any],
    *,
    family: str,
    action: str,
    requested: Optional[Dict[str, Any]] = None,
    success_mapper: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    failure_boundary: str = "backend",
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = dict(legacy_payload or {})
    if payload.get("status") == "ok":
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        mapped = success_mapper(data) if success_mapper is not None else dict(data)
        return action_success(
            family=family,
            action=action,
            requested=requested,
            result=mapped,
            fallback=fallback,
            legacy=payload,
        )
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return action_failure(
        family=family,
        action=action,
        code=str(error.get("code") or "action_failed"),
        message=str(error.get("message") or f"{action} failed"),
        retryable=bool(error.get("retryable")),
        requested=requested,
        details=error.get("details") if isinstance(error.get("details"), dict) else None,
        failure_boundary=str(error.get("boundary") or failure_boundary),
        fallback=fallback,
        unsupported=str(error.get("code") or "") == "unsupported_action",
        legacy=payload,
    )
