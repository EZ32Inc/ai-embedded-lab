from __future__ import annotations

import json
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


def append_task_result(report_root: str | Path, record: Dict) -> Path:
    md_path = _today_report_path(report_root)
    data_path = _today_data_path(report_root)

    records = _load_records(data_path)
    records.append(dict(record))
    data_path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")

    md_path.write_text(_render_markdown(records), encoding="utf-8")
    return md_path
