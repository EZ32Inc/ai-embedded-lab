#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "ai_behavior_results"
VERDICTS = ("PASS", "WEAK_PASS", "FAIL", "ERROR")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyYAML is required to load behavior case files") from exc
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = _load_yaml(path)
    if not isinstance(payload, list):
        raise RuntimeError(f"Case file must contain a top-level list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def load_case(path: Path, case_id: str) -> Dict[str, Any]:
    for item in load_cases(path):
        if str(item.get("case_id")) == case_id:
            return item
    raise RuntimeError(f"Case not found: {case_id}")


def _git_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _should_retry_retrieval(command: str, result: Dict[str, Any], attempt: int, max_attempts: int) -> bool:
    if attempt >= max_attempts:
        return False
    lowered = (str(result.get('stdout', '')) + "\n" + str(result.get('stderr', ''))).lower()
    transient_markers = (
        "permission denied: '/dev/ttyacm",
        'could not open /dev/ttyacm',
        'resource busy',
        'device or resource busy',
        'access is denied',
    )
    hardware_cmd = (
        'python3 -m ael verify-default run' in command
        or 'python3 -m ael run ' in command
        or 'idf.py' in command
    )
    return hardware_cmd and any(marker in lowered for marker in transient_markers)


def _run_command(command: str) -> Dict[str, Any]:
    max_attempts = 2
    attempts: List[Dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        started = datetime.now(timezone.utc)
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            shell=True,
            capture_output=True,
            text=True,
        )
        finished = datetime.now(timezone.utc)
        result = {
            "command": command,
            "argv": shlex.split(command),
            "returncode": int(completed.returncode),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "attempt": attempt,
            "started_at": started.isoformat(),
            "completed_at": finished.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 3),
        }
        attempts.append(result)
        if result["returncode"] == 0:
            break
        if not _should_retry_retrieval(command, result, attempt, max_attempts):
            break
        time.sleep(3)

    final = dict(attempts[-1])
    final["attempt_count"] = len(attempts)
    final["retried"] = len(attempts) > 1
    if len(attempts) > 1:
        final["attempts"] = attempts
        final["retry_reason"] = "transient hardware access failure detected"
    return final


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
        "input_json": payload,
    }


def render_answer_prompt(case: Dict[str, Any], retrievals: List[Dict[str, Any]]) -> str:
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


def render_judge_prompt(case: Dict[str, Any], retrievals: List[Dict[str, Any]], answer_text: str) -> str:
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
- Return a short judgment with one verdict from PASS/WEAK_PASS/FAIL/ERROR, reasons, and missing elements.
"""


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_output_dir(case_id: str | None = None) -> Path:
    base = ARTIFACT_ROOT / _timestamp_slug()
    if case_id:
        return base / case_id
    return base


def _answer_stage(case: Dict[str, Any], retrievals: List[Dict[str, Any]], answer_text: str | None) -> Dict[str, Any]:
    prompt = render_answer_prompt(case, retrievals)
    if answer_text:
        return {
            "mode": "provided_text",
            "status": "completed",
            "answer_text": answer_text,
            "answer_prompt": prompt,
        }
    return {
        "mode": "prompt_only",
        "status": "prompt_generated",
        "answer_text": None,
        "answer_prompt": prompt,
    }


def _answer_stage_external(
    case: Dict[str, Any],
    retrievals: List[Dict[str, Any]],
    answer_cmd: str,
) -> Dict[str, Any]:
    prompt = render_answer_prompt(case, retrievals)
    payload = {
        "stage": "answer",
        "case": case,
        "retrieval": retrievals,
        "answer_prompt": prompt,
    }
    result = _run_external_command(answer_cmd, payload)
    answer_text = result["stdout"].strip() or None
    status = "completed" if result["returncode"] == 0 else "error"
    return {
        "mode": "external_command",
        "status": status,
        "answer_text": answer_text,
        "answer_prompt": prompt,
        "answer_command": answer_cmd,
        "answer_return_code": result["returncode"],
        "answer_stdout": result["stdout"],
        "answer_stderr": result["stderr"],
    }


def _judge_stage(
    case: Dict[str, Any],
    retrievals: List[Dict[str, Any]],
    mode: str,
    answer_text: str,
    judge_verdict: str | None,
    judge_reason: str | None,
) -> Dict[str, Any]:
    prompt = render_judge_prompt(case, retrievals, answer_text or "<paste answer here>")
    retrieval_ok = all(int(item.get("returncode", 1)) == 0 for item in retrievals)

    if judge_verdict:
        return {
            "mode": "manual_verdict",
            "status": "completed",
            "verdict": judge_verdict,
            "reason": judge_reason or "manual verdict supplied",
            "judge_prompt": prompt,
            "verdict_source": "manual_verdict",
        }

    if mode == "stub":
        verdict = "WEAK_PASS" if retrieval_ok else "ERROR"
        reason = (
            "retrieval path executed successfully; semantic answer/judge review still pending"
            if retrieval_ok
            else "one or more retrieval commands failed"
        )
        return {
            "mode": "stub",
            "status": "completed",
            "verdict": verdict,
            "reason": reason,
            "judge_prompt": prompt,
            "verdict_source": "stub_logic",
        }

    verdict = "ERROR" if not retrieval_ok else "WEAK_PASS"
    reason = (
        "prompt-only mode produced prompts but no judge verdict was supplied"
        if retrieval_ok
        else "one or more retrieval commands failed before judging"
    )
    return {
        "mode": "prompt_only",
        "status": "prompt_generated",
        "verdict": verdict,
        "reason": reason,
        "judge_prompt": prompt,
        "verdict_source": "prompt_only_fallback",
    }


def _parse_external_judge_stdout(stdout: str) -> Dict[str, str] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        payload = None
    if isinstance(payload, dict):
        verdict = str(payload.get("verdict", "")).strip().upper()
        if verdict in VERDICTS:
            reason = str(payload.get("reason", "")).strip() or "parsed from judge JSON output"
            return {"verdict": verdict, "reason": reason}
    first = text.splitlines()[0].strip()
    if first in VERDICTS:
        reason_lines = text.splitlines()[1:]
        reason = "\n".join(reason_lines).strip() or "parsed from judge plain-text output"
        return {"verdict": first, "reason": reason}
    return None


def _judge_stage_external(
    case: Dict[str, Any],
    retrievals: List[Dict[str, Any]],
    answer_stage: Dict[str, Any],
    judge_cmd: str,
) -> Dict[str, Any]:
    answer_text = str(answer_stage.get("answer_text") or "")
    prompt = render_judge_prompt(case, retrievals, answer_text or "<no answer text>")
    payload = {
        "stage": "judge",
        "case": case,
        "retrieval": retrievals,
        "answer_stage": answer_stage,
        "judge_prompt": prompt,
    }
    result = _run_external_command(judge_cmd, payload)
    parsed = _parse_external_judge_stdout(result["stdout"])
    if result["returncode"] != 0:
        verdict = "ERROR"
        reason = "judge command failed"
        status = "error"
        verdict_source = "external_command_failure"
    elif parsed:
        verdict = parsed["verdict"]
        reason = parsed["reason"]
        status = "completed"
        verdict_source = "external_command_parsed"
    else:
        verdict = "ERROR"
        reason = "judge output could not be parsed"
        status = "completed"
        verdict_source = "external_command_fallback"
    return {
        "mode": "external_command",
        "status": status,
        "verdict": verdict,
        "reason": reason,
        "judge_prompt": prompt,
        "judge_command": judge_cmd,
        "judge_return_code": result["returncode"],
        "judge_stdout": result["stdout"],
        "judge_stderr": result["stderr"],
        "verdict_source": verdict_source,
    }


def run_case(
    case_file: Path,
    case: Dict[str, Any],
    mode: str = "prompt-only",
    answer_text: str | None = None,
    judge_verdict: str | None = None,
    judge_reason: str | None = None,
    answer_cmd: str | None = None,
    judge_cmd: str | None = None,
) -> Dict[str, Any]:
    retrieval_cmds = case.get("expected_retrieval_path", []) or []
    if not isinstance(retrieval_cmds, list) or not retrieval_cmds:
        raise RuntimeError("case has no expected_retrieval_path")

    retrievals: List[Dict[str, Any]] = []
    for cmd in retrieval_cmds:
        retrievals.append(_run_command(str(cmd)))

    if answer_cmd:
        answer = _answer_stage_external(case, retrievals, answer_cmd)
    else:
        answer = _answer_stage(case, retrievals, answer_text)
    answer_text_value = answer.get("answer_text") or ""
    if judge_cmd:
        judge = _judge_stage_external(case, retrievals, answer, judge_cmd)
    else:
        judge = _judge_stage(case, retrievals, mode, str(answer_text_value), judge_verdict, judge_reason)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "source_case_file": str(case_file),
        "case": dict(case),
        "retrieval": retrievals,
        "answer_stage": answer,
        "judge_stage": judge,
        "verdict": judge.get("verdict", "ERROR"),
        "answer_mode_used": answer.get("mode"),
        "judge_mode_used": judge.get("mode"),
        "verdict_source": judge.get("verdict_source", "legacy_or_stub"),
    }


def write_case_result(output_dir: Path, case_result: Dict[str, Any]) -> Path:
    case_id = str(case_result["case"].get("case_id"))
    out_path = _ensure_dir(output_dir) / f"{case_id}.json"
    out_path.write_text(json.dumps(case_result, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def print_case_header(case: Dict[str, Any]) -> None:
    print(f"case_id: {case.get('case_id')}")
    print(f"case_type: {case.get('case_type')}")
    print(f"intent_type: {case.get('intent_type')}")
    print(f"user_question: {case.get('user_question')}")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="run_ai_behavior_case.py")
    ap.add_argument("case_file")
    ap.add_argument("case_id", nargs="?")
    ap.add_argument("--list-cases", action="store_true")
    ap.add_argument("--mode", choices=("prompt-only", "stub"), default="prompt-only")
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--answer-cmd", default="")
    ap.add_argument("--judge-cmd", default="")
    ap.add_argument("--print-answer-prompt", action="store_true")
    ap.add_argument("--print-judge-prompt", action="store_true")
    ap.add_argument("--answer-text", default="")
    ap.add_argument("--judge-verdict", choices=VERDICTS, default="")
    ap.add_argument("--judge-reason", default="")
    ap.add_argument("--json-only", action="store_true")
    return ap.parse_args()


def _resolve_case_file(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise RuntimeError(f"case file not found: {path}")
    return path


def _resolve_output_dir(path_text: str, case_id: str) -> Path:
    if path_text:
        path = Path(path_text)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path
    return default_output_dir(case_id)


def main() -> int:
    args = _parse_args()
    try:
        case_file = _resolve_case_file(args.case_file)
        cases = load_cases(case_file)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_cases:
        for case in cases:
            print(f"{case.get('case_id')}\t{case.get('intent_type')}\t{case.get('user_question')}")
        return 0

    if not args.case_id:
        print("error: case_id is required unless --list-cases is used", file=sys.stderr)
        return 2

    try:
        case = load_case(case_file, args.case_id)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.json_only:
        print_case_header(case)
        for cmd in case.get("expected_retrieval_path", []) or []:
            print(f"retrieval_command: {cmd}")

    try:
        result = run_case(
            case_file=case_file,
            case=case,
            mode=args.mode,
            answer_text=args.answer_text or None,
            judge_verdict=args.judge_verdict or None,
            judge_reason=args.judge_reason or None,
            answer_cmd=args.answer_cmd or None,
            judge_cmd=args.judge_cmd or None,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output_dir = _resolve_output_dir(args.output_dir, str(case.get("case_id")))
    case_json = write_case_result(output_dir, result)

    if args.print_answer_prompt:
        print("---ANSWER_PROMPT---")
        print(result["answer_stage"]["answer_prompt"].rstrip())
    if args.print_judge_prompt:
        print("---JUDGE_PROMPT---")
        print(result["judge_stage"]["judge_prompt"].rstrip())

    if args.json_only:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["retrieval"]:
            print(f"retrieval_returncode: {item['returncode']}")
        print(f"verdict: {result['verdict']}")
        print(f"case_result_json: {case_json}")
        print(f"output_dir: {output_dir}")

    return 0 if result["verdict"] in ("PASS", "WEAK_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
