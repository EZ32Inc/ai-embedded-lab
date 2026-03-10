from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ael import inventory


def _consistency_checks(connection_setup: Dict[str, Any] | Any) -> List[Dict[str, Any]]:
    setup = connection_setup if isinstance(connection_setup, dict) else {}
    resolved_wiring = setup.get("resolved_wiring", {}) if isinstance(setup.get("resolved_wiring"), dict) else {}
    verification_views = setup.get("verification_views", {}) if isinstance(setup.get("verification_views"), dict) else {}
    warnings = list(setup.get("warnings") or []) if isinstance(setup.get("warnings"), list) else []

    checks: List[Dict[str, Any]] = []
    verify_target = str(resolved_wiring.get("verify") or "").strip()
    checks.append(
        {
            "name": "verify_mapping",
            "ok": bool(verify_target and verify_target != "UNKNOWN"),
            "detail": verify_target or "UNKNOWN",
        }
    )
    checks.append(
        {
            "name": "verification_views_present",
            "ok": bool(verification_views),
            "detail": sorted(verification_views.keys()),
        }
    )
    semantic_warning = next(
        (
            item
            for item in warnings
            if "observe_map.sig resolves" in str(item)
            or "verification view" in str(item)
            or "test pin" in str(item)
        ),
        None,
    )
    checks.append(
        {
            "name": "semantic_mapping_consistency",
            "ok": semantic_warning is None,
            "detail": semantic_warning or "ok",
        }
    )
    duplicate_warning = next((item for item in warnings if "observation points" in str(item)), None)
    checks.append(
        {
            "name": "duplicate_observation_points",
            "ok": duplicate_warning is None,
            "detail": duplicate_warning or "none",
        }
    )
    ground_warning = next((item for item in warnings if "ground_confirmed" in str(item)), None)
    checks.append(
        {
            "name": "ground_confirmation",
            "ok": ground_warning is None,
            "detail": ground_warning or "ok",
        }
    )
    return checks


def doctor(board_id: str, test_path: str, repo_root: str | Path | None = None) -> Dict[str, Any]:
    payload = inventory.describe_connection(board_id=board_id, test_path=test_path, repo_root=Path(repo_root) if repo_root else None)
    if not payload.get("ok"):
        return payload
    connection_setup = payload.get("connection_setup", {})
    validation_errors = list(payload.get("validation_errors") or [])
    checks = _consistency_checks(connection_setup)
    warnings = list(payload.get("warnings") or [])
    return {
        "ok": not validation_errors,
        "board": payload.get("board"),
        "test": payload.get("test"),
        "connection_setup": connection_setup,
        "connections": list(payload.get("connections") or []),
        "source_summary": dict(payload.get("source_summary") or {}),
        "warnings": warnings,
        "validation_errors": validation_errors,
        "consistency_checks": checks,
    }
