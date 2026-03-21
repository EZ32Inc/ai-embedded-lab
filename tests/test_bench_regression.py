from __future__ import annotations

import json
from pathlib import Path

import pytest

from ael_controlplane.bench_regression import (
    FAILURE_BOUNDARY_POLICY,
    action_policy_for_boundary,
    build_regression_snapshot,
    compare_regression_run,
    load_regression_history,
    render_regression_comparison_text,
    save_regression_snapshot,
)


def _snap(ok=True, pass_count=6, fail_count=0, boundaries=None, ts="2026-03-21T00:00:00Z"):
    return {
        "timestamp": ts,
        "run_id": f"run_{ts}",
        "ok": ok,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": pass_count + fail_count,
        "health_status": "pass" if ok else "fail",
        "baseline_readiness_status": "ready" if ok else "needs_attention",
        "failure_boundary_counts": dict(boundaries or {}),
        "failure_class_counts": {},
        "recovery_hint_counts": {},
        "instrument_health_counts": {},
        "instrument_family_counts": {},
        "schema_review_status": "aligned",
        "capability_taxonomy_version_counts": {},
        "status_health_schema_version_counts": {},
        "doctor_check_schema_version_counts": {},
    }


def test_failure_boundary_policy_covers_all_canonical_boundaries():
    expected = {
        "instrument_connectivity",
        "instrument_service",
        "instrument_measurement",
        "probe_health",
        "firmware_programming",
        "signal_capture",
        "instrument_health",
        "instrument_capabilities",
        "instrument_status",
        "interface_contract",
        "backend",
    }
    assert expected.issubset(set(FAILURE_BOUNDARY_POLICY.keys()))


def test_action_policy_for_boundary_returns_known_policy():
    policy = action_policy_for_boundary("probe_health")
    assert policy["boundary"] == "probe_health"
    assert policy["ai_action"] == "bounded_auto_retry"


def test_action_policy_for_unknown_boundary_returns_unknown():
    policy = action_policy_for_boundary("nonexistent_boundary")
    assert policy["boundary"] == "unknown"
    assert policy["ai_action"] == "open_investigation"


def test_build_regression_snapshot_from_state():
    state = {
        "ok": True,
        "pass_count": 6,
        "fail_count": 0,
        "total_count": 6,
        "health_status": "pass",
        "baseline_readiness_status": "ready",
        "failure_boundary_counts": {},
        "failure_class_counts": {},
        "recovery_hint_counts": {},
        "instrument_health_counts": {"ready": 6},
        "instrument_family_counts": {"stlink": 2, "esp32jtag": 4},
        "schema_review_status": "aligned",
        "capability_taxonomy_version_counts": {"instrument_capabilities/v1": 6},
        "status_health_schema_version_counts": {"instrument_status_health/v1": 6},
        "doctor_check_schema_version_counts": {"instrument_doctor_checks/v1": 6},
    }
    snap = build_regression_snapshot(state, run_id="2026-03-21_10-00-00", timestamp="2026-03-21T10:00:00Z")
    assert snap["ok"] is True
    assert snap["pass_count"] == 6
    assert snap["run_id"] == "2026-03-21_10-00-00"
    assert snap["timestamp"] == "2026-03-21T10:00:00Z"
    assert snap["instrument_family_counts"]["stlink"] == 2


def test_save_and_load_regression_history(tmp_path):
    snap1 = _snap(ts="2026-03-21T08:00:00Z")
    snap2 = _snap(ts="2026-03-21T09:00:00Z")
    save_regression_snapshot(snap1, tmp_path)
    save_regression_snapshot(snap2, tmp_path)
    history = load_regression_history(tmp_path, count=10)
    assert len(history) == 2
    assert history[0]["timestamp"] == "2026-03-21T08:00:00Z"
    assert history[1]["timestamp"] == "2026-03-21T09:00:00Z"


def test_load_regression_history_respects_count(tmp_path):
    for i in range(5):
        save_regression_snapshot(_snap(ts=f"2026-03-21T0{i}:00:00Z"), tmp_path)
    history = load_regression_history(tmp_path, count=3)
    assert len(history) == 3
    assert history[-1]["timestamp"] == "2026-03-21T04:00:00Z"


def test_load_regression_history_returns_empty_for_missing_file(tmp_path):
    assert load_regression_history(tmp_path / "nonexistent") == []


def test_compare_regression_run_stable_pass():
    history = [_snap(ok=True, ts="2026-03-21T00:00:00Z")]
    current = _snap(ok=True, ts="2026-03-21T01:00:00Z")
    result = compare_regression_run(current, history)
    assert result["trend"] == "stable_pass"
    assert result["pass_delta"] == 0
    assert result["fail_delta"] == 0
    assert result["new_boundaries"] == []
    assert result["action_policies"] == []


def test_compare_regression_run_regressed():
    history = [_snap(ok=True, pass_count=6, fail_count=0)]
    current = _snap(ok=False, pass_count=5, fail_count=1, boundaries={"probe_health": 1})
    result = compare_regression_run(current, history)
    assert result["trend"] == "regressed"
    assert result["fail_delta"] == 1
    assert "probe_health" in result["new_boundaries"]
    assert len(result["action_policies"]) == 1
    assert result["action_policies"][0]["occurrence"] == "first"
    assert result["action_policies"][0]["ai_action"] == "bounded_auto_retry"


def test_compare_regression_run_persistent_fail():
    history = [
        _snap(ok=False, boundaries={"probe_health": 1}, ts="2026-03-21T00:00:00Z"),
        _snap(ok=False, boundaries={"probe_health": 1}, ts="2026-03-21T01:00:00Z"),
    ]
    current = _snap(ok=False, boundaries={"probe_health": 1}, ts="2026-03-21T02:00:00Z")
    result = compare_regression_run(current, history)
    assert result["trend"] == "persistent_fail"
    assert "probe_health" in result["persistent_boundaries"]
    assert result["action_policies"][0]["occurrence"] == "repeated"


def test_compare_regression_run_recovered():
    history = [_snap(ok=False, boundaries={"probe_health": 1})]
    current = _snap(ok=True)
    result = compare_regression_run(current, history)
    assert result["trend"] == "recovered"
    assert result["resolved_boundaries"] == ["probe_health"]


def test_compare_regression_run_no_history():
    result = compare_regression_run(_snap(), [])
    assert result["trend"] == "no_history"
    assert result["first_run"] is True


def test_render_regression_comparison_text_contains_key_fields():
    history = [_snap(ok=True)]
    current = _snap(ok=False, fail_count=1, pass_count=5, boundaries={"signal_capture": 1})
    comparison = compare_regression_run(current, history)
    text = render_regression_comparison_text(current, comparison)
    assert "trend: regressed" in text
    assert "signal_capture" in text
    assert "open_investigation" in text
