#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List

from run_ai_behavior_case import REPO_ROOT, _git_commit, _timestamp_slug, load_case, run_case

REFERENCE_ROOT = REPO_ROOT / "tests" / "ai_behavior_cases" / "references"
APPROVED_ROOT = REFERENCE_ROOT / "approved"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "ai_behavior_references"


def _read_text(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.read_text(encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _run_external_command(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        shell=True,
        input=json.dumps(payload, indent=2, sort_keys=True),
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


def _required_elements(case: Dict[str, Any], answer_text: str) -> List[str]:
    lowered = answer_text.lower()
    missing = []
    for item in case.get("required_output_elements", []) or []:
        text = str(item).strip().lower()
        if text and text not in lowered:
            missing.append(str(item))
    return missing


def _semantic_compare_prompt() -> str:
    return """You are judging a fresh answer against an approved semantic baseline for an AEL AI behavior case.

Judge the fresh answer using the full context:
- case definition
- user question
- retrieval output
- approved reference answer
- fresh answer
- required output elements
- forbidden failure modes
- judge rubric

Return structured JSON with:
- verdict: PASS | WEAK_PASS | FAIL | ERROR
- reason: short explanation
- semantic_match: true/false
- grounded_in_retrieval: true/false
- required_elements_satisfied: true/false
- forbidden_failures_present: array of strings
- strengths: array of strings
- weaknesses: array of strings
"""


def _reference_md(case: Dict[str, Any], answer_text: str, retrieval: List[Dict[str, Any]]) -> str:
    retrieval_cmds = "\n".join(f"- `{item['command']}`" for item in retrieval)
    return "\n".join(
        [
            f"# {case.get('case_id')}",
            "",
            "## Question",
            "",
            str(case.get("user_question", "")),
            "",
            "## Approved Answer Draft",
            "",
            answer_text.strip(),
            "",
            "## Retrieval Path",
            "",
            retrieval_cmds,
            "",
        ]
    )


def _resolve_case_file(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise RuntimeError(f"case file not found: {path}")
    return path


def _draft_output_dir(output_dir: str) -> Path:
    if output_dir:
        path = Path(output_dir)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = ARTIFACT_ROOT / _timestamp_slug()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _approved_json_path(case_id: str) -> Path:
    APPROVED_ROOT.mkdir(parents=True, exist_ok=True)
    return APPROVED_ROOT / f"{case_id}.json"


def _approved_md_path(case_id: str) -> Path:
    APPROVED_ROOT.mkdir(parents=True, exist_ok=True)
    return APPROVED_ROOT / f"{case_id}.md"


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="ai_behavior_reference.py")
    sub = ap.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft")
    draft.add_argument("case_file")
    draft.add_argument("case_id")
    draft.add_argument("--answer-text", default="")
    draft.add_argument("--answer-file", default="")
    draft.add_argument("--output-dir", default="")

    approve = sub.add_parser("approve")
    approve.add_argument("--draft-json", required=True)

    compare = sub.add_parser("compare")
    compare.add_argument("case_file")
    compare.add_argument("case_id")
    compare.add_argument("--answer-text", default="")
    compare.add_argument("--answer-file", default="")
    compare.add_argument("--reference-json", default="")
    compare.add_argument("--output-dir", default="")
    compare.add_argument("--judge-cmd", default="")
    return ap.parse_args()


def _answer_text(answer_text: str, answer_file: str) -> str:
    if answer_text:
        return answer_text
    if answer_file:
        return _read_text(answer_file)
    raise RuntimeError("answer text is required via --answer-text or --answer-file")


def _load_reference_json(path_text: str, case_id: str) -> Dict[str, Any]:
    if path_text:
        path = Path(path_text)
        if not path.is_absolute():
            path = REPO_ROOT / path
    else:
        path = _approved_json_path(case_id)
    if not path.exists():
        raise RuntimeError(f"approved reference not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid reference JSON: {path}")
    return payload


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _cmd_draft(args: argparse.Namespace) -> int:
    case_file = _resolve_case_file(args.case_file)
    case = load_case(case_file, args.case_id)
    answer = _answer_text(args.answer_text, args.answer_file)
    run = run_case(case_file=case_file, case=case, mode="prompt-only", answer_text=answer)
    out_dir = _draft_output_dir(args.output_dir)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "source_case_file": str(case_file),
        "case": dict(case),
        "question": case.get("user_question"),
        "approved_answer_draft": answer,
        "retrieval": run["retrieval"],
        "status": "draft",
    }
    json_path = out_dir / f"{args.case_id}.draft.json"
    md_path = out_dir / f"{args.case_id}.draft.md"
    _write_json(json_path, payload)
    md_path.write_text(_reference_md(case, answer, run["retrieval"]), encoding="utf-8")
    print(f"draft_json: {json_path}")
    print(f"draft_md: {md_path}")
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft_json)
    if not draft_path.is_absolute():
        draft_path = REPO_ROOT / draft_path
    if not draft_path.exists():
        print(f"error: draft not found: {draft_path}", file=sys.stderr)
        return 2
    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print(f"error: invalid draft JSON: {draft_path}", file=sys.stderr)
        return 2
    case_id = str(payload.get("case", {}).get("case_id"))
    payload["status"] = "approved"
    payload["approved_at"] = datetime.now(timezone.utc).isoformat()
    payload["approved_from"] = str(draft_path)
    json_path = _approved_json_path(case_id)
    md_path = _approved_md_path(case_id)
    _write_json(json_path, payload)
    draft_md = draft_path.with_name(draft_path.name.replace(".draft.json", ".draft.md"))
    if draft_md.exists():
        shutil.copyfile(draft_md, md_path)
    else:
        md_path.write_text(
            _reference_md(payload["case"], str(payload.get("approved_answer_draft", "")), payload.get("retrieval", [])),
            encoding="utf-8",
        )
    print(f"approved_json: {json_path}")
    print(f"approved_md: {md_path}")
    return 0


def _comparison_verdict(case: Dict[str, Any], approved_answer: str, fresh_answer: str) -> Dict[str, Any]:
    approved_norm = _normalize(approved_answer)
    fresh_norm = _normalize(fresh_answer)
    missing_required = _required_elements(case, fresh_answer)
    similarity = SequenceMatcher(None, approved_norm, fresh_norm).ratio() if approved_norm or fresh_norm else 1.0
    if fresh_norm == approved_norm:
        missing_required = []
        verdict = "PASS"
        reason = "fresh answer matches approved reference after normalization"
    elif not missing_required:
        verdict = "WEAK_PASS"
        reason = "fresh answer differs from approved reference but still contains required elements"
    else:
        verdict = "FAIL"
        reason = "fresh answer is missing required elements from the case contract"
    return {
        "verdict": verdict,
        "reason": reason,
        "similarity": similarity,
        "missing_required_elements": missing_required,
    }


def _parse_semantic_judge_output(stdout: str) -> Dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    verdict = str(payload.get("verdict", "")).strip().upper()
    if verdict not in {"PASS", "WEAK_PASS", "FAIL", "ERROR"}:
        return None
    return {
        "verdict": verdict,
        "reason": str(payload.get("reason", "")).strip() or "semantic judge did not provide a reason",
        "semantic_match": bool(payload.get("semantic_match", False)),
        "grounded_in_retrieval": bool(payload.get("grounded_in_retrieval", False)),
        "required_elements_satisfied": bool(payload.get("required_elements_satisfied", False)),
        "forbidden_failures_present": payload.get("forbidden_failures_present", []),
        "strengths": payload.get("strengths", []),
        "weaknesses": payload.get("weaknesses", []),
    }


def _semantic_compare(
    case: Dict[str, Any],
    reference: Dict[str, Any],
    retrieval: List[Dict[str, Any]],
    fresh_answer: str,
    judge_cmd: str,
) -> Dict[str, Any]:
    payload = {
        "stage": "reference_compare_judge",
        "case": case,
        "user_question": case.get("user_question"),
        "expected_retrieval_path": case.get("expected_retrieval_path", []),
        "retrieval": retrieval,
        "approved_reference": {
            "question": reference.get("question"),
            "approved_answer": reference.get("approved_answer_draft"),
            "status": reference.get("status"),
        },
        "fresh_answer": fresh_answer,
        "required_output_elements": case.get("required_output_elements", []),
        "forbidden_failure_modes": case.get("forbidden_failure_modes", []),
        "judge_rubric": case.get("judge_rubric", []),
        "semantic_judge_prompt": _semantic_compare_prompt(),
    }
    result = _run_external_command(judge_cmd, payload)
    parsed = _parse_semantic_judge_output(result["stdout"])
    if result["returncode"] != 0:
        return {
            "mode": "external_semantic_judge",
            "status": "error",
            "judge_command": judge_cmd,
            "judge_return_code": result["returncode"],
            "judge_stdout": result["stdout"],
            "judge_stderr": result["stderr"],
            "verdict": "ERROR",
            "reason": "semantic judge command failed",
            "verdict_source": "semantic_judge_failure",
            "judge_input_summary": payload,
        }
    if not parsed:
        return {
            "mode": "external_semantic_judge",
            "status": "error",
            "judge_command": judge_cmd,
            "judge_return_code": result["returncode"],
            "judge_stdout": result["stdout"],
            "judge_stderr": result["stderr"],
            "verdict": "ERROR",
            "reason": "semantic judge output could not be parsed",
            "verdict_source": "semantic_judge_unparsed",
            "judge_input_summary": payload,
        }
    return {
        "mode": "external_semantic_judge",
        "status": "completed",
        "judge_command": judge_cmd,
        "judge_return_code": result["returncode"],
        "judge_stdout": result["stdout"],
        "judge_stderr": result["stderr"],
        "verdict": parsed["verdict"],
        "reason": parsed["reason"],
        "verdict_source": "semantic_judge",
        "judge_input_summary": payload,
        "judge_output": parsed,
    }


def _cmd_compare(args: argparse.Namespace) -> int:
    case_file = _resolve_case_file(args.case_file)
    case = load_case(case_file, args.case_id)
    fresh_answer = _answer_text(args.answer_text, args.answer_file)
    reference = _load_reference_json(args.reference_json, args.case_id)
    approved_answer = str(reference.get("approved_answer_draft", ""))
    run = run_case(case_file=case_file, case=case, mode="prompt-only", answer_text=fresh_answer)
    retrieval_failed = any(int(item.get("returncode", 1)) != 0 for item in run["retrieval"])
    if retrieval_failed:
        comparison = {
            "mode": "retrieval_gate",
            "status": "error",
            "verdict": "ERROR",
            "reason": "retrieval stage failed; compare was not executed",
            "verdict_source": "retrieval_failure",
        }
    elif args.judge_cmd:
        comparison = _semantic_compare(case, reference, run["retrieval"], fresh_answer, args.judge_cmd)
    else:
        fallback = _comparison_verdict(case, approved_answer, fresh_answer)
        comparison = {
            "mode": "mechanical_fallback",
            "status": "completed",
            "verdict": fallback["verdict"],
            "reason": fallback["reason"],
            "verdict_source": "mechanical_fallback",
            "comparison_details": fallback,
        }
    out_dir = _draft_output_dir(args.output_dir)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "source_case_file": str(case_file),
        "case": dict(case),
        "reference_path": args.reference_json or str(_approved_json_path(args.case_id)),
        "approved_answer": approved_answer,
        "fresh_answer": fresh_answer,
        "retrieval": run["retrieval"],
        "comparison": comparison,
        "verdict": comparison["verdict"],
    }
    json_path = out_dir / f"{args.case_id}.compare.json"
    _write_json(json_path, payload)
    retrieval_failed = any(int(item.get("returncode", 1)) != 0 for item in run["retrieval"])
    if retrieval_failed:
        print("retrieval_status: failed")
    else:
        print("retrieval_status: completed")
    print(f"verdict: {comparison['verdict']}")
    print(f"reason: {comparison['reason']}")
    print(f"compare_json: {json_path}")
    return 0 if comparison["verdict"] in ("PASS", "WEAK_PASS") else 1


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "draft":
            return _cmd_draft(args)
        if args.command == "approve":
            return _cmd_approve(args)
        if args.command == "compare":
            return _cmd_compare(args)
        print(f"error: unsupported command {args.command}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
