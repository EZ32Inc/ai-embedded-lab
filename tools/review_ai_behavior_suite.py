#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_summary_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if path.is_dir():
        path = path / "summary.json"
    if not path.exists():
        raise RuntimeError(f"summary file not found: {path}")
    return path


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"summary must be a JSON object: {path}")
    return payload


def _case_result_path(summary_path: Path, case_id: str) -> Path:
    return summary_path.parent / f"{case_id}.json"


def _extract_reason(case_path: Path) -> str | None:
    if not case_path.exists():
        return None
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    judge = payload.get("judge_stage")
    if isinstance(judge, dict):
        value = judge.get("reason")
        if isinstance(value, str) and value:
            return value
    return None


def _print_case_lines(summary_path: Path, cases: List[Dict[str, Any]], only_attention: bool) -> None:
    for item in cases:
        case_id = str(item.get("case_id"))
        verdict = str(item.get("verdict"))
        if only_attention and verdict not in ("FAIL", "ERROR"):
            continue
        reason = _extract_reason(_case_result_path(summary_path, case_id))
        if reason:
            print(f"- {case_id}: {verdict} | {reason}")
        else:
            print(f"- {case_id}: {verdict}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="review_ai_behavior_suite.py")
    ap.add_argument("suite_result", help="suite output dir or summary.json path")
    ap.add_argument("--only-attention", action="store_true", help="show only FAIL/ERROR cases")
    args = ap.parse_args()

    try:
        summary_path = _resolve_summary_path(args.suite_result)
        summary = _load_json(summary_path)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    counts = summary.get("counts", {})
    print(f"suite: {summary_path.parent}")
    print(f"case_file: {summary.get('case_file')}")
    print(f"mode: {summary.get('mode')}")
    print(f"total_cases: {summary.get('total_cases')}")
    print(f"PASS: {counts.get('PASS', 0)}")
    print(f"WEAK_PASS: {counts.get('WEAK_PASS', 0)}")
    print(f"FAIL: {counts.get('FAIL', 0)}")
    print(f"ERROR: {counts.get('ERROR', 0)}")

    failed_ids = summary.get("failed_or_error_case_ids", []) or []
    if failed_ids:
        print("attention_cases:")
        _print_case_lines(summary_path, summary.get("cases", []), only_attention=True)
    else:
        print("attention_cases: none")

    if not args.only_attention:
        print("all_cases:")
        _print_case_lines(summary_path, summary.get("cases", []), only_attention=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
