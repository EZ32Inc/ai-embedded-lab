from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List


def _today_report_path(report_root: str | Path) -> Path:
    d = date.today().isoformat()
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"nightly_{d}.md"


def _init_report(path: Path) -> None:
    if path.exists():
        return
    title_date = path.stem.replace("nightly_", "")
    content = [
        f"# Nightly Report {title_date}",
        "",
        "## DONE",
        "",
        "## FAILED",
        "",
        "## Human action required",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def _insert_under_heading(lines: List[str], heading: str, entry: str) -> List[str]:
    idx = -1
    for i, line in enumerate(lines):
        if line.strip() == heading:
            idx = i
            break
    if idx < 0:
        lines.extend([heading, "", entry, ""])
        return lines

    insert_at = idx + 1
    while insert_at < len(lines):
        cur = lines[insert_at].strip()
        if cur.startswith("## "):
            break
        insert_at += 1
    lines.insert(insert_at, entry)
    return lines


def append_task_result(report_root: str | Path, record: Dict) -> Path:
    path = _today_report_path(report_root)
    _init_report(path)

    task_id = str(record.get("task_id", ""))
    run_dir = str(record.get("run_dir", ""))
    ok = bool(record.get("ok", False))
    duration_s = record.get("duration_s")
    try:
        duration_txt = f"{float(duration_s):.2f}s"
    except Exception:
        duration_txt = "n/a"

    if ok:
        entry = f"- {task_id} | run_dir={run_dir} | ok=true | duration={duration_txt}"
        heading = "## DONE"
    else:
        error_summary = str(record.get("error_summary", ""))
        entry = f"- {task_id} | run_dir={run_dir} | ok=false | error={error_summary}"
        heading = "## FAILED"

    lines = path.read_text(encoding="utf-8").splitlines()
    lines = _insert_under_heading(lines, heading, entry)

    err = str(record.get("error_summary", "")).lower()
    needs_human = []
    for token in ("permission", "sudo", "device not found", "download mode"):
        if token in err:
            needs_human.append(token)

    for token in needs_human:
        hint = f"- {task_id}: human action required ({token})"
        lines = _insert_under_heading(lines, "## Human action required", hint)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
