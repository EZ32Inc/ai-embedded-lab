#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from run_ai_behavior_case import (
    REPO_ROOT,
    VERDICTS,
    _ensure_dir,
    _timestamp_slug,
    load_cases,
    run_case,
    write_case_result,
)


def _resolve_case_file(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise RuntimeError(f"case file not found: {path}")
    return path


def _default_output_dir() -> Path:
    return REPO_ROOT / "artifacts" / "ai_behavior_results" / _timestamp_slug()


def _summary_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# AI Behavior Suite Summary",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- case_file: `{summary['case_file']}`",
        f"- mode: `{summary['mode']}`",
        f"- base_mode: `{summary.get('base_mode', summary['mode'])}`",
        f"- total_cases: `{summary['total_cases']}`",
        f"- PASS: `{summary['counts']['PASS']}`",
        f"- WEAK_PASS: `{summary['counts']['WEAK_PASS']}`",
        f"- FAIL: `{summary['counts']['FAIL']}`",
        f"- ERROR: `{summary['counts']['ERROR']}`",
        "",
    ]
    if summary.get("answer_cmd"):
        lines.insert(5, f"- answer_cmd: `{summary['answer_cmd']}`")
    if summary.get("judge_cmd"):
        insert_at = 6 if summary.get("answer_cmd") else 5
        lines.insert(insert_at, f"- judge_cmd: `{summary['judge_cmd']}`")
    if summary["failed_or_error_case_ids"]:
        lines.append("## Failed Or Error Cases")
        lines.append("")
        for case_id in summary["failed_or_error_case_ids"]:
            lines.append(f"- `{case_id}`")
        lines.append("")
    lines.append("## Cases")
    lines.append("")
    for item in summary["cases"]:
        lines.append(f"- `{item['case_id']}`: `{item['verdict']}`")
    lines.append("")
    return "\n".join(lines)


def _counts(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {value: 0 for value in VERDICTS}
    for item in cases:
        verdict = str(item.get("verdict", "ERROR"))
        counts.setdefault(verdict, 0)
        counts[verdict] += 1
    return counts


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="run_ai_behavior_suite.py")
    ap.add_argument("case_file")
    ap.add_argument("--mode", choices=("prompt-only", "stub"), default="prompt-only")
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rerun-from-summary", default="")
    ap.add_argument("--answer-cmd", default="")
    ap.add_argument("--judge-cmd", default="")
    return ap.parse_args()


def _effective_mode(base_mode: str, answer_cmd: str, judge_cmd: str) -> str:
    if answer_cmd or judge_cmd:
        return "external-command"
    return base_mode


def _load_summary_case_ids(path_text: str) -> List[str]:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise RuntimeError(f"summary file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"summary file must contain a JSON object: {path}")
    values = payload.get("failed_or_error_case_ids", [])
    if not isinstance(values, list):
        raise RuntimeError(f"summary file missing failed_or_error_case_ids list: {path}")
    return [str(item) for item in values]


def main() -> int:
    args = _parse_args()
    try:
        case_file = _resolve_case_file(args.case_file)
        cases = load_cases(case_file)
    except Exception as exc:
        print(f"error: {exc}")
        return 2

    if args.rerun_from_summary:
        try:
            rerun_ids = set(_load_summary_case_ids(args.rerun_from_summary))
        except Exception as exc:
            print(f"error: {exc}")
            return 2
        cases = [case for case in cases if str(case.get("case_id")) in rerun_ids]

    if args.limit > 0:
        cases = cases[: args.limit]
    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir()
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    _ensure_dir(output_dir)

    print(f"case_file: {case_file}")
    effective_mode = _effective_mode(args.mode, args.answer_cmd, args.judge_cmd)
    print(f"mode: {effective_mode}")
    print(f"output_dir: {output_dir}")
    if args.rerun_from_summary:
        print(f"rerun_from_summary: {args.rerun_from_summary}")
    if args.answer_cmd:
        print(f"answer_cmd: {args.answer_cmd}")
    if args.judge_cmd:
        print(f"judge_cmd: {args.judge_cmd}")

    case_rows: List[Dict[str, Any]] = []
    suite_exit = 0
    for case in cases:
        case_id = str(case.get("case_id"))
        print(f"running_case: {case_id}")
        try:
            result = run_case(
                case_file=case_file,
                case=case,
                mode=args.mode,
                answer_cmd=args.answer_cmd or None,
                judge_cmd=args.judge_cmd or None,
            )
        except Exception as exc:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_case_file": str(case_file),
                "case": dict(case),
                "retrieval": [],
                "answer_stage": {"mode": args.mode, "status": "error"},
                "judge_stage": {
                    "mode": args.mode,
                    "status": "error",
                    "verdict": "ERROR",
                    "reason": str(exc),
                },
                "verdict": "ERROR",
            }
        write_case_result(output_dir, result)
        verdict = str(result.get("verdict", "ERROR"))
        if verdict not in ("PASS", "WEAK_PASS"):
            suite_exit = 1
        case_rows.append({"case_id": case_id, "verdict": verdict})
        print(f"case_verdict: {case_id} {verdict}")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_file": str(case_file),
        "mode": effective_mode,
        "base_mode": args.mode,
        "answer_cmd": args.answer_cmd or None,
        "judge_cmd": args.judge_cmd or None,
        "total_cases": len(case_rows),
        "counts": _counts(case_rows),
        "failed_or_error_case_ids": [item["case_id"] for item in case_rows if item["verdict"] in ("FAIL", "ERROR")],
        "cases": case_rows,
    }
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "summary.md"
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md.write_text(_summary_markdown(summary), encoding="utf-8")

    print(f"summary_json: {summary_json}")
    print(f"summary_md: {summary_md}")
    print(f"total_cases: {summary['total_cases']}")
    print(f"PASS: {summary['counts']['PASS']}")
    print(f"WEAK_PASS: {summary['counts']['WEAK_PASS']}")
    print(f"FAIL: {summary['counts']['FAIL']}")
    print(f"ERROR: {summary['counts']['ERROR']}")

    return suite_exit


if __name__ == "__main__":
    raise SystemExit(main())
