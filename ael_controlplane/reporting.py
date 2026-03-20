from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Dict, List


_STATUS_ORDER = ["PASS", "FAIL", "SKIP", "HUMAN_ACTION_REQUIRED"]


def _today_slug() -> str:
    return date.today().isoformat()


def _today_report_path(report_root: str | Path) -> Path:
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"nightly_{_today_slug()}.md"


def _today_data_path(report_root: str | Path) -> Path:
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"nightly_{_today_slug()}.json"


def _load_records(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [x for x in payload if isinstance(x, dict)]


def _task_gate_rows(record: Dict) -> List[Dict]:
    rows = []
    gates = record.get("gate_results", [])
    if isinstance(gates, list):
        for g in gates:
            if not isinstance(g, dict):
                continue
            rows.append(g)
    if rows:
        return rows

    # Fallback for tasks without explicit gate payloads.
    rows.append(
        {
            "name": "task",
            "status": "PASS" if bool(record.get("ok", False)) else "FAIL",
            "summary": str(record.get("error_summary", "")),
            "command": "",
            "hints": [],
        }
    )
    return rows


def _status_counts(records: List[Dict]) -> Dict[str, int]:
    counts = {k: 0 for k in _STATUS_ORDER}
    for rec in records:
        for gate in _task_gate_rows(rec):
            status = str(gate.get("status", "")).upper()
            if status in counts:
                counts[status] += 1
    return counts


def _duration_text(record: Dict) -> str:
    try:
        return f"{float(record.get('duration_s')):.2f}s"
    except Exception:
        return "n/a"


def _rerun_cmd(gate: Dict) -> str:
    cmd = str(gate.get("command", "")).strip()
    return cmd if cmd else "n/a"


def _render_markdown(records: List[Dict]) -> str:
    day = _today_slug()
    lines: List[str] = [f"# Nightly Report {day}", ""]

    counts = _status_counts(records)
    lines.extend(["## Status Counts", ""])
    for key in _STATUS_ORDER:
        lines.append(f"- {key}: {counts.get(key, 0)}")
    lines.append("")

    lines.extend(["## Tasks", ""])
    for rec in records:
        task_id = str(rec.get("task_id", ""))
        run_dir = str(rec.get("run_dir", ""))
        ok = bool(rec.get("ok", False))
        lines.append(f"- {task_id} | run_dir={run_dir} | ok={str(ok).lower()} | duration={_duration_text(rec)}")
        for gate in _task_gate_rows(rec):
            name = str(gate.get("name", "gate"))
            status = str(gate.get("status", "")).upper() or "PASS"
            summary = str(gate.get("summary", ""))
            lines.append(f"  - {name}: {status} | {summary}")
            if status in ("FAIL", "HUMAN_ACTION_REQUIRED"):
                lines.append(f"    - rerun: {_rerun_cmd(gate)}")
        lines.append("")

    lines.extend(["## Action Required", ""])
    for rec in records:
        task_id = str(rec.get("task_id", ""))
        for gate in _task_gate_rows(rec):
            status = str(gate.get("status", "")).upper()
            if status != "HUMAN_ACTION_REQUIRED":
                continue
            summary = str(gate.get("summary", ""))
            lines.append(f"- {task_id} | {summary}")
            hints = gate.get("hints", [])
            if isinstance(hints, list):
                for h in hints:
                    lines.append(f"  - {str(h)}")
            lines.append(f"  - rerun: {_rerun_cmd(gate)}")
    lines.append("")

    lines.extend(["## Skipped", ""])
    for rec in records:
        task_id = str(rec.get("task_id", ""))
        for gate in _task_gate_rows(rec):
            status = str(gate.get("status", "")).upper()
            if status != "SKIP":
                continue
            summary = str(gate.get("summary", ""))
            lines.append(f"- {task_id} | {summary}")
            lines.append(f"  - rerun: {_rerun_cmd(gate)}")
    lines.append("")

    return "\n".join(lines)


def default_verification_review_summary(repo_root: str | Path | None = None) -> Dict[str, str | bool]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["python3", "-m", "ael", "verify-default", "review"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    text = (proc.stdout or "").strip()
    if proc.returncode == 0 and text:
        return {"ok": True, "text": text}
    error = (proc.stderr or proc.stdout or "").strip() or f"verify-default review exited with code {proc.returncode}"
    return {"ok": False, "text": text, "error": error}


def default_verification_review_highlights(review: Dict[str, str | bool]) -> Dict[str, str]:
    text = str(review.get("text") or "")
    highlights = {
        "health_status": "unavailable",
        "schema_review_status": "unavailable",
        "warning_summary": "unavailable",
        "structured_coverage": "unavailable",
        "instrument_families": "unavailable",
        "instrument_health": "unavailable",
        "failure_boundaries": "unavailable",
        "recovery_hints": "unavailable",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("health_status:"):
            highlights["health_status"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("schema_review_status:"):
            highlights["schema_review_status"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("warning_summary:"):
            highlights["warning_summary"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("structured_coverage:"):
            highlights["structured_coverage"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("instrument_families:"):
            highlights["instrument_families"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("instrument_health:"):
            highlights["instrument_health"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("failure_boundaries:"):
            highlights["failure_boundaries"] = stripped.split(":", 1)[1].strip() or "unavailable"
        elif stripped.startswith("recovery_hints:"):
            highlights["recovery_hints"] = stripped.split(":", 1)[1].strip() or "unavailable"
    if not bool(review.get("ok", False)) and highlights["warning_summary"] == "unavailable":
        highlights["warning_summary"] = "review unavailable"
    return highlights


def _baseline_readiness_from_review_payload(payload: Dict[str, str | bool]) -> str:
    health = str(payload.get("health_status") or "").strip()
    schema = str(payload.get("schema_review_status") or "").strip()
    warning_summary = str(payload.get("warning_summary") or "").strip()
    if health in ("fail", "partial_pass"):
        return "needs_attention"
    if health in ("unknown", "unavailable", ""):
        return "unavailable"
    if warning_summary not in ("", "none", "unavailable"):
        return "needs_attention"
    if schema in ("warnings_present", "partial_structured_coverage"):
        return "needs_attention"
    if health == "pass" and schema in ("aligned", "no_schema_signals"):
        return "ready"
    return "needs_attention"


def default_verification_review_payload(review: Dict[str, str | bool]) -> Dict[str, str | bool]:
    payload = dict(review)
    payload.update(default_verification_review_highlights(payload))
    payload["ok"] = bool(payload.get("ok", False))
    payload["text"] = str(payload.get("text") or payload.get("error") or "")
    if payload["text"] and not str(payload.get("error") or ""):
        payload["error"] = ""
    payload["baseline_readiness_status"] = _baseline_readiness_from_review_payload(payload)
    return payload


def default_verification_review_snapshot(repo_root: str | Path | None = None) -> Dict[str, str | bool]:
    return default_verification_review_payload(default_verification_review_summary(repo_root))


def append_task_result(report_root: str | Path, record: Dict) -> Path:
    md_path = _today_report_path(report_root)
    data_path = _today_data_path(report_root)

    records = _load_records(data_path)
    records.append(dict(record))
    data_path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")

    md_path.write_text(_render_markdown(records), encoding="utf-8")
    return md_path
