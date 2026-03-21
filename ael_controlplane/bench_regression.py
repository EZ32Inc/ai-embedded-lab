"""Recurring bench regression baseline utilities.

Provides:
- FAILURE_BOUNDARY_POLICY  — action policy table keyed by failure_boundary
- save_regression_snapshot  — persist a structured run summary to the log
- load_regression_history   — read recent log entries
- compare_regression_run    — compare current summary against recent history
- build_regression_summary  — assemble a single timestamped snapshot dict
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Action policy table keyed by failure_boundary
# ---------------------------------------------------------------------------

FAILURE_BOUNDARY_POLICY: Dict[str, Dict[str, str]] = {
    "instrument_connectivity": {
        "boundary": "instrument_connectivity",
        "description": "instrument or probe network endpoint is unreachable",
        "first_occurrence": "retry once; if still failing inspect bench wiring and power",
        "repeated_occurrence": "mark instrument degraded; do not retry until connectivity is restored",
        "ai_action": "bounded_auto_retry",
    },
    "instrument_service": {
        "boundary": "instrument_service",
        "description": "instrument transport or service API is not responding",
        "first_occurrence": "restart the relevant daemon or service and retry",
        "repeated_occurrence": "escalate to human; service may need a manual restart or reprobe",
        "ai_action": "bounded_auto_retry",
    },
    "instrument_measurement": {
        "boundary": "instrument_measurement",
        "description": "instrument responded but measurement result was unexpected",
        "first_occurrence": "stop retrying; open technical investigation of test logic or DUT state",
        "repeated_occurrence": "file as regression; do not auto-retry",
        "ai_action": "open_investigation",
    },
    "probe_health": {
        "boundary": "probe_health",
        "description": "control instrument (JTAG/SWD probe) reported a health failure",
        "first_occurrence": "rerun preflight; if still failing inspect probe USB and power",
        "repeated_occurrence": "mark probe degraded; do not use for firmware programming until healthy",
        "ai_action": "bounded_auto_retry",
    },
    "firmware_programming": {
        "boundary": "firmware_programming",
        "description": "firmware flash or GDB load operation failed",
        "first_occurrence": "retry after probe recovery; confirm target power is stable",
        "repeated_occurrence": "stop retrying; escalate to human for wiring or firmware investigation",
        "ai_action": "bounded_auto_retry",
    },
    "signal_capture": {
        "boundary": "signal_capture",
        "description": "digital capture or logic-analyzer operation failed",
        "first_occurrence": "rerun preflight and verify capture wiring; retry once",
        "repeated_occurrence": "stop retrying; open investigation of capture hardware or wiring",
        "ai_action": "open_investigation",
    },
    "instrument_health": {
        "boundary": "instrument_health",
        "description": "instrument self-reported unhealthy via doctor output",
        "first_occurrence": "run doctor command; if fixable recover and retry once",
        "repeated_occurrence": "mark instrument degraded; do not schedule work until healthy",
        "ai_action": "bounded_auto_retry",
    },
    "instrument_capabilities": {
        "boundary": "instrument_capabilities",
        "description": "capability query failed or returned unexpected shape",
        "first_occurrence": "inspect instrument interface and retry",
        "repeated_occurrence": "flag as interface regression; requires investigation",
        "ai_action": "open_investigation",
    },
    "instrument_status": {
        "boundary": "instrument_status",
        "description": "status query failed unexpectedly",
        "first_occurrence": "retry after connectivity check",
        "repeated_occurrence": "flag as interface regression",
        "ai_action": "bounded_auto_retry",
    },
    "interface_contract": {
        "boundary": "interface_contract",
        "description": "action was called that is not supported by this instrument family",
        "first_occurrence": "check capability advertisement; action may be misrouted",
        "repeated_occurrence": "flag as orchestration bug; do not retry",
        "ai_action": "open_investigation",
    },
    "backend": {
        "boundary": "backend",
        "description": "backend adapter returned an error of unclassified origin",
        "first_occurrence": "inspect adapter logs; retry once",
        "repeated_occurrence": "flag for investigation",
        "ai_action": "bounded_auto_retry",
    },
}

_UNKNOWN_BOUNDARY_POLICY: Dict[str, str] = {
    "boundary": "unknown",
    "description": "failure boundary is not classified",
    "first_occurrence": "inspect run logs and classify manually",
    "repeated_occurrence": "escalate to human",
    "ai_action": "open_investigation",
}


def action_policy_for_boundary(failure_boundary: str) -> Dict[str, str]:
    """Return the action policy entry for a given failure_boundary string."""
    return FAILURE_BOUNDARY_POLICY.get(str(failure_boundary).strip(), _UNKNOWN_BOUNDARY_POLICY)


# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------

_LOG_FILENAME = "bench_regression_log.json"


def _log_path(report_root: str | Path) -> Path:
    return Path(report_root) / _LOG_FILENAME


def build_regression_snapshot(
    state: Dict[str, Any],
    *,
    run_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a compact timestamped snapshot from a verify-default state dict."""
    ts = timestamp or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    pass_count = int(state.get("pass_count") or 0)
    fail_count = int(state.get("fail_count") or 0)
    total_count = int(state.get("total_count") or (pass_count + fail_count))
    return {
        "timestamp": ts,
        "run_id": str(run_id or state.get("run_id") or ""),
        "ok": bool(state.get("ok", fail_count == 0)),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": total_count,
        "health_status": str(state.get("health_status") or "unknown"),
        "baseline_readiness_status": str(state.get("baseline_readiness_status") or "unknown"),
        "failure_boundary_counts": dict(state.get("failure_boundary_counts") or {}),
        "failure_class_counts": dict(state.get("failure_class_counts") or {}),
        "recovery_hint_counts": dict(state.get("recovery_hint_counts") or {}),
        "instrument_health_counts": dict(state.get("instrument_health_counts") or {}),
        "instrument_family_counts": dict(state.get("instrument_family_counts") or {}),
        "schema_review_status": str(state.get("schema_review_status") or ""),
        "capability_taxonomy_version_counts": dict(state.get("capability_taxonomy_version_counts") or {}),
        "status_health_schema_version_counts": dict(state.get("status_health_schema_version_counts") or {}),
        "doctor_check_schema_version_counts": dict(state.get("doctor_check_schema_version_counts") or {}),
    }


def save_regression_snapshot(
    snapshot: Dict[str, Any],
    report_root: str | Path,
) -> Path:
    """Append a snapshot to the regression log and return the log path."""
    log = _log_path(report_root)
    log.parent.mkdir(parents=True, exist_ok=True)
    history: List[Dict[str, Any]] = []
    if log.exists():
        try:
            raw = json.loads(log.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                history = [x for x in raw if isinstance(x, dict)]
        except Exception:
            history = []
    history.append(snapshot)
    log.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
    return log


def load_regression_history(
    report_root: str | Path,
    count: int = 10,
) -> List[Dict[str, Any]]:
    """Load the most recent `count` regression snapshots (newest last)."""
    log = _log_path(report_root)
    if not log.exists():
        return []
    try:
        raw = json.loads(log.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    entries = [x for x in raw if isinstance(x, dict)]
    return entries[-count:]


# ---------------------------------------------------------------------------
# Comparison / trend analysis
# ---------------------------------------------------------------------------

def _is_first_occurrence(failure_boundary: str, recent: List[Dict[str, Any]]) -> bool:
    """Return True if failure_boundary did not appear in any of the recent runs."""
    for snap in recent:
        if failure_boundary in (snap.get("failure_boundary_counts") or {}):
            return False
    return True


def compare_regression_run(
    current: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare current snapshot against recent history and return a trend summary."""
    if not history:
        return {
            "trend": "no_history",
            "first_run": True,
            "pass_delta": None,
            "fail_delta": None,
            "new_boundaries": [],
            "persistent_boundaries": [],
            "resolved_boundaries": [],
            "action_policies": [],
        }

    prev = history[-1]
    pass_delta = current.get("pass_count", 0) - prev.get("pass_count", 0)
    fail_delta = current.get("fail_count", 0) - prev.get("fail_count", 0)

    current_boundaries = set((current.get("failure_boundary_counts") or {}).keys())
    prev_boundaries = set((prev.get("failure_boundary_counts") or {}).keys())

    new_boundaries = sorted(current_boundaries - prev_boundaries)
    resolved_boundaries = sorted(prev_boundaries - current_boundaries)
    persistent_boundaries = sorted(current_boundaries & prev_boundaries)

    # Classify each current failure boundary
    action_policies: List[Dict[str, str]] = []
    for boundary in sorted(current_boundaries):
        is_first = _is_first_occurrence(boundary, history[:-1])  # all but the most recent
        policy = action_policy_for_boundary(boundary)
        action_policies.append({
            "boundary": boundary,
            "occurrence": "first" if is_first else "repeated",
            "ai_action": policy["ai_action"],
            "guidance": policy["first_occurrence"] if is_first else policy["repeated_occurrence"],
        })

    if current.get("ok") and prev.get("ok"):
        trend = "stable_pass"
    elif not current.get("ok") and not prev.get("ok"):
        trend = "persistent_fail" if persistent_boundaries else "fail"
    elif current.get("ok") and not prev.get("ok"):
        trend = "recovered"
    else:
        trend = "regressed"

    return {
        "trend": trend,
        "first_run": False,
        "pass_delta": pass_delta,
        "fail_delta": fail_delta,
        "new_boundaries": new_boundaries,
        "persistent_boundaries": persistent_boundaries,
        "resolved_boundaries": resolved_boundaries,
        "action_policies": action_policies,
    }


def render_regression_comparison_text(
    current: Dict[str, Any],
    comparison: Dict[str, Any],
) -> str:
    """Render a human-readable summary of the regression comparison."""
    lines = [
        f"bench_regression_run: {current.get('timestamp', '')}",
        f"run_id: {current.get('run_id', '')}",
        f"result: {'PASS' if current.get('ok') else 'FAIL'} "
        f"({current.get('pass_count', 0)}/{current.get('total_count', 0)})",
        f"trend: {comparison.get('trend', 'unknown')}",
    ]

    pass_delta = comparison.get("pass_delta")
    fail_delta = comparison.get("fail_delta")
    if pass_delta is not None:
        sign = "+" if pass_delta >= 0 else ""
        lines.append(f"pass_delta: {sign}{pass_delta}")
    if fail_delta is not None:
        sign = "+" if fail_delta >= 0 else ""
        lines.append(f"fail_delta: {sign}{fail_delta}")

    new_b = comparison.get("new_boundaries") or []
    if new_b:
        lines.append(f"new_failure_boundaries: {', '.join(new_b)}")

    resolved_b = comparison.get("resolved_boundaries") or []
    if resolved_b:
        lines.append(f"resolved_failure_boundaries: {', '.join(resolved_b)}")

    persistent_b = comparison.get("persistent_boundaries") or []
    if persistent_b:
        lines.append(f"persistent_failure_boundaries: {', '.join(persistent_b)}")

    for policy_entry in comparison.get("action_policies") or []:
        boundary = policy_entry.get("boundary", "")
        occurrence = policy_entry.get("occurrence", "")
        ai_action = policy_entry.get("ai_action", "")
        guidance = policy_entry.get("guidance", "")
        lines.append(f"  boundary={boundary} [{occurrence}] -> {ai_action}: {guidance}")

    if comparison.get("first_run"):
        lines.append("note: no prior history; this is the first recorded baseline run")

    return "\n".join(lines) + "\n"
