from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


EVIDENCE_VERSION = "evidence/0.1"


def status_from_ok(ok: Any) -> str:
    return "pass" if bool(ok) else "fail"


def make_item(
    *,
    kind: str,
    source: str,
    ok: Any,
    summary: str,
    facts: Dict[str, Any] | None = None,
    artifacts: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "kind": str(kind or "").strip(),
        "source": str(source or "").strip(),
        "status": status_from_ok(ok),
        "summary": str(summary or "").strip(),
        "facts": facts if isinstance(facts, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }


def write_evidence(run_dir: str | Path, filename: str, payload: Dict[str, Any] | Any) -> str:
    if not filename or not str(filename).strip():
        raise ValueError("filename is required")

    base = Path(run_dir)
    artifacts_dir = base / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    out_path = artifacts_dir / str(filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    return str(out_path)


def collect_from_runner_result(runner_result: Dict[str, Any] | Any) -> List[Dict[str, Any]]:
    if not isinstance(runner_result, dict):
        return []
    items: List[Dict[str, Any]] = []
    steps = runner_result.get("steps", [])
    if not isinstance(steps, list):
        return []
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        out = entry.get("result", {})
        if not isinstance(out, dict):
            continue
        raw = out.get("evidence")
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            continue
        for item in raw:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip()
            source = str(item.get("source") or entry.get("type") or "").strip()
            status = str(item.get("status") or "").strip().lower()
            if not kind or not source or status not in {"pass", "fail", "info"}:
                continue
            items.append(
                {
                    "kind": kind,
                    "source": source,
                    "status": status,
                    "summary": str(item.get("summary") or "").strip(),
                    "facts": item.get("facts") if isinstance(item.get("facts"), dict) else {},
                    "artifacts": item.get("artifacts") if isinstance(item.get("artifacts"), dict) else {},
                }
            )
    recovery = runner_result.get("recovery", [])
    if isinstance(recovery, list):
        for r in recovery:
            if not isinstance(r, dict):
                continue
            result = r.get("result", {}) if isinstance(r.get("result"), dict) else {}
            items.append(
                make_item(
                    kind="recovery.action",
                    source=str(r.get("action_type") or "recovery"),
                    ok=r.get("ok", False),
                    summary=(result.get("error_summary") or f"recovery action {r.get('action_type')}"),
                    facts={
                        "step": r.get("step"),
                        "failure_kind": r.get("failure_kind"),
                        "recovery_hint": r.get("recovery_hint") if isinstance(r.get("recovery_hint"), dict) else {},
                        "action_type": r.get("action_type"),
                        "ok": r.get("ok", False),
                    },
                    artifacts={},
                )
            )
    return items


def write_runner_evidence(run_dir: str | Path, runner_result: Dict[str, Any] | Any, filename: str = "evidence.json") -> str:
    items = collect_from_runner_result(runner_result)
    payload = {"version": EVIDENCE_VERSION, "items": items}
    return write_evidence(run_dir, filename, payload)
