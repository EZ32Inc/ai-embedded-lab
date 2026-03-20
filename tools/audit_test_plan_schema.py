from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ael.test_plan_schema import extract_plan_metadata


def _family_key(payload: Dict[str, Any], path: Path) -> str:
    board = str(payload.get("board") or "").strip()
    if board:
        for suffix in ("_stlink", "_esp32jtag"):
            if board.endswith(suffix):
                return board[: -len(suffix)]
        return board
    name = str(payload.get("name") or path.stem).strip()
    token = name.split("_", 1)[0].strip()
    return token or "unknown"


def build_report(repo_root: Path) -> Dict[str, Any]:
    plans_dir = repo_root / "tests" / "plans"
    plans: List[Dict[str, Any]] = []
    structured_count = 0
    legacy_count = 0
    invalid_count = 0

    legacy_mailbox_candidates: List[str] = []
    invalid_structured: List[str] = []
    structured_ready: List[str] = []
    missing_required_metadata: List[str] = []
    family_summary: Dict[str, Dict[str, int]] = {}
    test_kind_summary: Dict[str, int] = {}

    for path in sorted(plans_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = extract_plan_metadata(payload)
        family = _family_key(payload, path)
        schema_version = metadata.get("schema_version") or "legacy"
        test_kind = str(metadata.get("test_kind") or "").strip() or None
        validation_errors = list(metadata.get("validation_errors") or [])
        has_mailbox = isinstance(payload.get("mailbox_verify"), dict)
        missing_core = []
        if schema_version != "legacy":
            for field in ("schema_version", "test_kind", "name"):
                if not payload.get(field):
                    missing_core.append(field)
        family_entry = family_summary.setdefault(
            family,
            {
                "plan_count": 0,
                "structured_count": 0,
                "legacy_count": 0,
                "legacy_mailbox_candidate_count": 0,
                "invalid_structured_count": 0,
            },
        )
        family_entry["plan_count"] += 1
        if schema_version == "legacy":
            legacy_count += 1
            family_entry["legacy_count"] += 1
            if has_mailbox:
                legacy_mailbox_candidates.append(path.relative_to(repo_root).as_posix())
                family_entry["legacy_mailbox_candidate_count"] += 1
        else:
            structured_count += 1
            family_entry["structured_count"] += 1
            test_kind_summary[test_kind or "structured_unspecified"] = test_kind_summary.get(test_kind or "structured_unspecified", 0) + 1
            if validation_errors:
                invalid_structured.append(path.relative_to(repo_root).as_posix())
                family_entry["invalid_structured_count"] += 1
            else:
                structured_ready.append(path.relative_to(repo_root).as_posix())
            if missing_core:
                missing_required_metadata.append(path.relative_to(repo_root).as_posix())
        if validation_errors:
            invalid_count += 1
        plans.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "name": payload.get("name") or path.stem,
                "schema_version": schema_version,
                "test_kind": metadata.get("test_kind"),
                "labels": metadata.get("labels"),
                "covers": metadata.get("covers"),
                "requires": metadata.get("requires"),
                "supported_instruments": metadata.get("supported_instruments"),
                "validation_errors": validation_errors,
                "is_mailbox_candidate": has_mailbox,
                "missing_required_metadata": missing_core,
            }
        )

    structured_share = (structured_count / len(plans)) if plans else 0.0
    readiness = {
        "status": (
            "ready"
            if not invalid_structured and not legacy_mailbox_candidates and not missing_required_metadata
            else "needs_attention"
        ),
        "structured_share": round(structured_share, 3),
        "invalid_structured_zero": not invalid_structured,
        "legacy_mailbox_zero": not legacy_mailbox_candidates,
        "missing_required_metadata_zero": not missing_required_metadata,
    }
    review_status = "aligned"
    if invalid_structured or missing_required_metadata:
        review_status = "warnings_present"
    elif legacy_count:
        review_status = "partial_structured_coverage"
    warning_messages: List[str] = []
    if invalid_structured:
        warning_messages.append(f"invalid structured plans present ({len(invalid_structured)})")
    if missing_required_metadata:
        warning_messages.append(f"missing required metadata present ({len(missing_required_metadata)})")
    if legacy_mailbox_candidates:
        warning_messages.append(f"legacy mailbox candidates present ({len(legacy_mailbox_candidates)})")
    schema_review = {
        "status": review_status,
        "structured_coverage": {
            "structured_count": structured_count,
            "legacy_count": legacy_count,
        },
        "test_kind_distribution": dict(sorted(test_kind_summary.items())),
        "warning_summary": {
            "count": len(warning_messages),
            "messages": warning_messages,
        },
    }

    return {
        "ok": True,
        "repo_root": str(repo_root),
        "readiness": readiness,
        "schema_review": schema_review,
        "summary": {
            "plan_count": len(plans),
            "structured_count": structured_count,
            "legacy_count": legacy_count,
            "invalid_count": invalid_count,
            "structured_ready_count": len(structured_ready),
            "legacy_mailbox_candidate_count": len(legacy_mailbox_candidates),
            "invalid_structured_count": len(invalid_structured),
            "missing_required_metadata_count": len(missing_required_metadata),
        },
        "migration": {
            "structured_ready": structured_ready,
            "legacy_mailbox_candidates": legacy_mailbox_candidates,
            "invalid_structured": invalid_structured,
            "missing_required_metadata": missing_required_metadata,
        },
        "test_kind_summary": dict(sorted(test_kind_summary.items())),
        "family_summary": dict(sorted(family_summary.items())),
        "plans": plans,
    }


def render_text(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    readiness = report.get("readiness") or {}
    schema_review = report.get("schema_review") or {}
    lines = [
        "Test plan schema audit",
        f"readiness_status: {readiness.get('status')}",
        f"schema_review_status: {schema_review.get('status')}",
        f"structured_share: {readiness.get('structured_share', 0.0)}",
        f"invalid_structured_zero: {readiness.get('invalid_structured_zero')}",
        f"legacy_mailbox_zero: {readiness.get('legacy_mailbox_zero')}",
        f"missing_required_metadata_zero: {readiness.get('missing_required_metadata_zero')}",
        "",
        f"plan_count: {summary.get('plan_count', 0)}",
        f"structured_count: {summary.get('structured_count', 0)}",
        f"legacy_count: {summary.get('legacy_count', 0)}",
        f"invalid_count: {summary.get('invalid_count', 0)}",
        f"structured_ready_count: {summary.get('structured_ready_count', 0)}",
        f"legacy_mailbox_candidate_count: {summary.get('legacy_mailbox_candidate_count', 0)}",
        f"invalid_structured_count: {summary.get('invalid_structured_count', 0)}",
        f"missing_required_metadata_count: {summary.get('missing_required_metadata_count', 0)}",
        "",
    ]
    lines.append("schema_review:")
    coverage = schema_review.get("structured_coverage") or {}
    lines.append(
        f"  structured_coverage: structured={coverage.get('structured_count', 0)} legacy={coverage.get('legacy_count', 0)}"
    )
    warning_summary = schema_review.get("warning_summary") or {}
    lines.append(f"  warning_summary: {warning_summary.get('count', 0)}")
    for item in warning_summary.get("messages") or []:
        lines.append(f"    - {item}")
    lines.append("")
    migration = report.get("migration") or {}
    lines.append("migration:")
    for key in ("structured_ready", "legacy_mailbox_candidates", "invalid_structured", "missing_required_metadata"):
        lines.append(f"  {key}: {len(migration.get(key) or [])}")
    lines.append("")
    test_kind_summary = report.get("test_kind_summary") or {}
    lines.append("test_kind_summary:")
    for test_kind, count in test_kind_summary.items():
        lines.append(f"  {test_kind}: {count}")
    lines.append("")
    family_summary = report.get("family_summary") or {}
    lines.append("family_summary:")
    for family, stats in family_summary.items():
        lines.append(
            f"  {family}: structured={stats.get('structured_count', 0)} "
            f"legacy={stats.get('legacy_count', 0)} "
            f"legacy_mailbox={stats.get('legacy_mailbox_candidate_count', 0)} "
            f"invalid_structured={stats.get('invalid_structured_count', 0)}"
        )
    lines.append("")
    for plan in report.get("plans") or []:
        lines.append(f"{plan.get('path')} [{plan.get('schema_version')}]")
        if plan.get("test_kind"):
            lines.append(f"  test_kind: {plan.get('test_kind')}")
        if plan.get("supported_instruments"):
            lines.append("  supported_instruments: " + ", ".join(plan.get("supported_instruments") or []))
        if plan.get("labels"):
            lines.append("  labels: " + ", ".join(plan.get("labels") or []))
        if plan.get("covers"):
            lines.append("  covers: " + ", ".join(plan.get("covers") or []))
        if isinstance(plan.get("requires"), dict) and plan.get("requires"):
            lines.append("  requires: " + json.dumps(plan.get("requires"), sort_keys=True))
        if plan.get("validation_errors"):
            lines.append("  validation_errors:")
            for item in plan.get("validation_errors") or []:
                lines.append(f"    - {item}")
        if plan.get("missing_required_metadata"):
            lines.append("  missing_required_metadata: " + ", ".join(plan.get("missing_required_metadata") or []))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report = build_report(Path(args.repo_root).resolve())
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
