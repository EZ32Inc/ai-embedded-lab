#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyYAML is required to load behavior case files") from exc
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_case(path: Path, case_id: str) -> Dict[str, Any]:
    payload = _load_yaml(path)
    if not isinstance(payload, list):
        raise RuntimeError(f"Case file must contain a top-level list: {path}")
    for item in payload:
        if isinstance(item, dict) and str(item.get("case_id")) == case_id:
            return item
    raise RuntimeError(f"Case not found: {case_id}")


def _run_command(command: str) -> Dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        shell=True,
        capture_output=True,
        text=True,
    )
    return {
        "command": command,
        "argv": shlex.split(command),
        "returncode": int(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _render_answer_prompt(case: Dict[str, Any], retrievals: List[Dict[str, Any]]) -> str:
    return f"""You are answering an AEL AI behavior test case.

Case metadata:
- case_id: {case.get('case_id')}
- case_type: {case.get('case_type')}
- intent_type: {case.get('intent_type')}

User question:
{case.get('user_question')}

Expected retrieval path:
{json.dumps(case.get('expected_retrieval_path', []), indent=2)}

Required output elements:
{json.dumps(case.get('required_output_elements', []), indent=2)}

Forbidden failure modes:
{json.dumps(case.get('forbidden_failure_modes', []), indent=2)}

Retrieval results:
{json.dumps(retrievals, indent=2, sort_keys=True)}

Instructions:
- Answer the user question using the retrieval results above.
- Stay grounded in the retrieval output.
- Include the required output elements.
- Avoid the forbidden failure modes.
- Do not pretend additional validation happened.
"""


def _render_judge_prompt(case: Dict[str, Any], retrievals: List[Dict[str, Any]], answer_text: str) -> str:
    return f"""You are judging an AEL AI behavior test case.

Case metadata:
{json.dumps({
    'case_id': case.get('case_id'),
    'case_type': case.get('case_type'),
    'intent_type': case.get('intent_type'),
    'user_question': case.get('user_question'),
    'expected_retrieval_path': case.get('expected_retrieval_path', []),
    'must_use_formal_path': case.get('must_use_formal_path'),
    'required_output_elements': case.get('required_output_elements', []),
    'forbidden_failure_modes': case.get('forbidden_failure_modes', []),
    'judge_rubric': case.get('judge_rubric', []),
}, indent=2, sort_keys=True)}

Retrieval results:
{json.dumps(retrievals, indent=2, sort_keys=True)}

Candidate answer:
{answer_text}

Judge instructions:
- Decide whether the answer followed the expected retrieval path.
- Check whether required output elements are present.
- Check whether any forbidden failure mode occurred.
- Check whether the answer is grounded and avoids semantic overclaim.
- Return a short judgment with pass/fail, reasons, and any missing elements.
"""


def _bundle(case_file: Path, case: Dict[str, Any], retrievals: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_file": str(case_file),
        "case": {
            "case_id": case.get("case_id"),
            "case_type": case.get("case_type"),
            "intent_type": case.get("intent_type"),
            "user_question": case.get("user_question"),
            "expected_retrieval_path": case.get("expected_retrieval_path", []),
            "must_use_formal_path": bool(case.get("must_use_formal_path", False)),
            "required_output_elements": case.get("required_output_elements", []),
            "forbidden_failure_modes": case.get("forbidden_failure_modes", []),
            "judge_rubric": case.get("judge_rubric", []),
            "notes": case.get("notes"),
        },
        "retrieval": retrievals,
        "answer_prompt": _render_answer_prompt(case, retrievals),
        "judge_prompt_template": _render_judge_prompt(case, retrievals, "<paste answer here>"),
        "automation": {
            "answer_generation": "prompt_assisted",
            "judge": "prompt_assisted",
        },
    }


def _print_case_header(case: Dict[str, Any]) -> None:
    print(f"case_id: {case.get('case_id')}")
    print(f"case_type: {case.get('case_type')}")
    print(f"intent_type: {case.get('intent_type')}")
    print(f"user_question: {case.get('user_question')}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_ai_behavior_case.py")
    ap.add_argument("case_file")
    ap.add_argument("case_id")
    ap.add_argument("--print-answer-prompt", action="store_true")
    ap.add_argument("--print-judge-prompt", action="store_true")
    ap.add_argument("--answer-text", default="")
    ap.add_argument("--write-json", default="")
    args = ap.parse_args()

    case_file = Path(args.case_file)
    if not case_file.is_absolute():
        case_file = REPO_ROOT / case_file
    if not case_file.exists():
        print(f"error: case file not found: {case_file}", file=sys.stderr)
        return 2

    try:
        case = _load_case(case_file, args.case_id)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_case_header(case)
    retrieval_cmds = case.get("expected_retrieval_path", []) or []
    if not isinstance(retrieval_cmds, list) or not retrieval_cmds:
        print("error: case has no expected_retrieval_path", file=sys.stderr)
        return 2

    retrievals: List[Dict[str, Any]] = []
    for cmd in retrieval_cmds:
        cmd_str = str(cmd)
        print(f"retrieval_command: {cmd_str}")
        result = _run_command(cmd_str)
        retrievals.append(result)
        print(f"retrieval_returncode: {result['returncode']}")

    payload = _bundle(case_file, case, retrievals)

    if args.write_json:
        out_path = Path(args.write_json)
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"result_json: {out_path}")

    if args.print_answer_prompt:
        print("---ANSWER_PROMPT---")
        print(payload["answer_prompt"].rstrip())

    if args.print_judge_prompt:
        answer_text = args.answer_text or "<paste answer here>"
        print("---JUDGE_PROMPT---")
        print(_render_judge_prompt(case, retrievals, answer_text).rstrip())

    if not args.print_answer_prompt and not args.print_judge_prompt:
        print(json.dumps(payload, indent=2, sort_keys=True))

    retrieval_ok = all(int(item.get("returncode", 1)) == 0 for item in retrievals)
    return 0 if retrieval_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
