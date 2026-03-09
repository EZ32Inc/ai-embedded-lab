import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _env():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    return env


def _write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_single_case_runner_persists_case_result(tmp_path):
    out_dir = tmp_path / "case_out"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "inventory_current_duts_001",
            "--mode",
            "stub",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "verdict: WEAK_PASS" in res.stdout
    case_json = out_dir / "inventory_current_duts_001.json"
    payload = json.loads(case_json.read_text(encoding="utf-8"))
    assert payload["case"]["case_id"] == "inventory_current_duts_001"
    assert payload["retrieval"][0]["command"] == "python3 -m ael inventory list"
    assert payload["judge_stage"]["verdict"] == "WEAK_PASS"
    assert payload["answer_stage"]["status"] == "prompt_generated"


def test_single_case_runner_can_print_answer_prompt(tmp_path):
    out_dir = tmp_path / "case_prompt"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "describe_test_stm32f401_001",
            "--output-dir",
            str(out_dir),
            "--print-answer-prompt",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    assert "---ANSWER_PROMPT---" in res.stdout
    assert "Please show me stm32f401rct6 golden GPIO test connections" in res.stdout
    assert "python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/gpio_signature.json" in res.stdout


def test_suite_runner_emits_summary_and_case_files(tmp_path):
    out_dir = tmp_path / "suite_out"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_suite.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "--mode",
            "stub",
            "--limit",
            "2",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "total_cases: 2" in res.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_cases"] == 2
    assert summary["counts"]["WEAK_PASS"] == 2
    assert (out_dir / "summary.md").exists()
    assert (out_dir / "inventory_current_duts_001.json").exists()


def test_single_case_runner_can_list_cases():
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "--list-cases",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "inventory_current_duts_001" in res.stdout
    assert "describe_test_stm32f401_001" in res.stdout


def test_load_cases_supports_baseline_manifest():
    from tools.run_ai_behavior_case import load_cases

    cases = load_cases(REPO_ROOT / "tests" / "ai_behavior_cases" / "baselines" / "v1.yaml")
    assert [case["case_id"] for case in cases] == [
        "inventory_current_duts_001",
        "describe_test_stm32f401_001",
        "explain_stage_plan_stm32f401_001",
        "default_verification_review_001",
    ]


def test_suite_runner_can_rerun_failed_or_error_cases_only(tmp_path):
    out_dir = tmp_path / "suite_rerun"
    summary_path = tmp_path / "prior_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "failed_or_error_case_ids": [
                    "inventory_board_tests_stm32f401_001",
                ]
            }
        ),
        encoding="utf-8",
    )
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_suite.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "--mode",
            "stub",
            "--rerun-from-summary",
            str(summary_path),
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "running_case: inventory_board_tests_stm32f401_001" in res.stdout
    assert "inventory_current_duts_001" not in res.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_cases"] == 1
    assert summary["cases"][0]["case_id"] == "inventory_board_tests_stm32f401_001"


def test_suite_runner_accepts_baseline_manifest(tmp_path):
    out_dir = tmp_path / "baseline_suite_out"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_suite.py",
            "tests/ai_behavior_cases/baselines/v1.yaml",
            "--mode",
            "stub",
            "--limit",
            "2",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "total_cases: 2" in res.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_cases"] == 2
    assert summary["cases"][0]["case_id"] == "inventory_current_duts_001"
    assert summary["cases"][1]["case_id"] == "describe_test_stm32f401_001"


def test_review_helper_prints_human_digest(tmp_path):
    out_dir = tmp_path / "suite_review"
    subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_suite.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "--mode",
            "stub",
            "--limit",
            "2",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    res = subprocess.run(
        [
            sys.executable,
            "tools/review_ai_behavior_suite.py",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "total_cases: 2" in res.stdout
    assert "attention_cases: none" in res.stdout
    assert "inventory_current_duts_001: WEAK_PASS" in res.stdout


def test_single_case_runner_supports_external_answer_and_judge_commands(tmp_path):
    answer_script = _write_script(
        tmp_path / "fake_answer.py",
        (
            "import json, sys\n"
            "payload = json.load(sys.stdin)\n"
            "assert payload['stage'] == 'answer'\n"
            "print('Answer generated from external command')\n"
        ),
    )
    judge_script = _write_script(
        tmp_path / "fake_judge.py",
        (
            "import json, sys\n"
            "payload = json.load(sys.stdin)\n"
            "assert payload['stage'] == 'judge'\n"
            "assert 'Answer generated from external command' in payload['answer_stage']['answer_text']\n"
            "print(json.dumps({'verdict': 'PASS', 'reason': 'external judge accepted answer'}))\n"
        ),
    )
    out_dir = tmp_path / "external_case"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "inventory_current_duts_001",
            "--output-dir",
            str(out_dir),
            "--answer-cmd",
            f"{sys.executable} {answer_script}",
            "--judge-cmd",
            f"{sys.executable} {judge_script}",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "verdict: PASS" in res.stdout
    payload = json.loads((out_dir / "inventory_current_duts_001.json").read_text(encoding="utf-8"))
    assert payload["answer_stage"]["mode"] == "external_command"
    assert payload["answer_stage"]["answer_return_code"] == 0
    assert payload["answer_stage"]["answer_text"] == "Answer generated from external command"
    assert payload["judge_stage"]["mode"] == "external_command"
    assert payload["judge_stage"]["verdict"] == "PASS"
    assert payload["verdict_source"] == "external_command_parsed"


def test_single_case_runner_external_judge_failure_falls_back_to_error(tmp_path):
    judge_script = _write_script(
        tmp_path / "bad_judge.py",
        "print('not a parseable verdict')\n",
    )
    out_dir = tmp_path / "bad_judge_case"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "inventory_current_duts_001",
            "--output-dir",
            str(out_dir),
            "--answer-text",
            "manual answer",
            "--judge-cmd",
            f"{sys.executable} {judge_script}",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    assert "verdict: ERROR" in res.stdout
    payload = json.loads((out_dir / "inventory_current_duts_001.json").read_text(encoding="utf-8"))
    assert payload["judge_stage"]["verdict"] == "ERROR"
    assert payload["judge_stage"]["verdict_source"] == "external_command_fallback"


def test_suite_runner_supports_external_answer_and_judge_commands(tmp_path):
    answer_script = _write_script(
        tmp_path / "suite_answer.py",
        "import json, sys\njson.load(sys.stdin)\nprint('suite external answer')\n",
    )
    judge_script = _write_script(
        tmp_path / "suite_judge.py",
        "import json, sys\njson.load(sys.stdin)\nprint('{\"verdict\":\"PASS\",\"reason\":\"suite external judge\"}')\n",
    )
    out_dir = tmp_path / "suite_external"
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_suite.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "--limit",
            "2",
            "--output-dir",
            str(out_dir),
            "--answer-cmd",
            f"{sys.executable} {answer_script}",
            "--judge-cmd",
            f"{sys.executable} {judge_script}",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_env(),
        check=True,
    )
    assert "PASS: 2" in res.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["PASS"] == 2
    assert summary["mode"] == "external-command"
    assert summary["answer_cmd"]
    assert summary["judge_cmd"]


def test_reference_workflow_draft_approve_and_compare(tmp_path):
    out_dir = tmp_path / "reference_workflow"
    approved_root = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_root / "inventory_current_duts_001.json"
    approved_md = approved_root / "inventory_current_duts_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None

    try:
        draft = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "draft",
                "tests/ai_behavior_cases/organic_cases.yaml",
                "inventory_current_duts_001",
                "--answer-text",
                "current DUT ids\nMCU names or families\ntest names grouped by DUT or otherwise clearly associated",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "draft_json:" in draft.stdout
        draft_json = out_dir / "inventory_current_duts_001.draft.json"
        assert draft_json.exists()

        approve = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "approve",
                "--draft-json",
                str(draft_json),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "approved_json:" in approve.stdout
        assert approved_json.exists()

        compare = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                "tests/ai_behavior_cases/organic_cases.yaml",
                "inventory_current_duts_001",
                "--answer-text",
                "current DUT ids\nMCU names or families\ntest names grouped by DUT or otherwise clearly associated",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "verdict: PASS" in compare.stdout
        compare_json = out_dir / "inventory_current_duts_001.compare.json"
        payload = json.loads(compare_json.read_text(encoding="utf-8"))
        assert payload["comparison"]["verdict"] == "PASS"
        assert payload["comparison"]["verdict_source"] == "mechanical_fallback"
        assert payload["comparison"]["comparison_details"]["missing_required_elements"] == []
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_reference_compare_prefers_semantic_judge_when_provided(tmp_path):
    approved_root = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_root / "inventory_current_duts_001.json"
    approved_md = approved_root / "inventory_current_duts_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None
    judge_script = _write_script(
        tmp_path / "semantic_judge.py",
        (
            "import json, sys\n"
            "payload = json.load(sys.stdin)\n"
            "assert payload['stage'] == 'reference_compare_judge'\n"
            "assert payload['approved_reference']['approved_answer']\n"
            "assert payload['fresh_answer']\n"
            "print(json.dumps({"
            "'verdict': 'PASS',"
            "'reason': 'semantic judge accepted answer',"
            "'semantic_match': True,"
            "'grounded_in_retrieval': True,"
            "'required_elements_satisfied': True,"
            "'forbidden_failures_present': [],"
            "'strengths': ['matches approved answer semantically'],"
            "'weaknesses': []"
            "}))\n"
        ),
    )

    try:
        approved_root.mkdir(parents=True, exist_ok=True)
        approved_json.write_text(
            json.dumps(
                {
                    "case": {"case_id": "inventory_current_duts_001"},
                    "question": "What DUTs and tests do we currently have?",
                    "approved_answer_draft": "Reference baseline answer",
                    "status": "approved",
                }
            ),
            encoding="utf-8",
        )
        approved_md.write_text("Reference baseline answer", encoding="utf-8")

        out_dir = tmp_path / "semantic_compare"
        res = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                "tests/ai_behavior_cases/organic_cases.yaml",
                "inventory_current_duts_001",
                "--answer-text",
                "Fresh semantic answer",
                "--judge-cmd",
                f"{sys.executable} {judge_script}",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "verdict: PASS" in res.stdout
        payload = json.loads((out_dir / "inventory_current_duts_001.compare.json").read_text(encoding="utf-8"))
        assert payload["comparison"]["verdict"] == "PASS"
        assert payload["comparison"]["verdict_source"] == "semantic_judge"
        assert payload["comparison"]["judge_output"]["semantic_match"] is True
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_reference_compare_can_use_captured_retrieval_file(tmp_path):
    approved_root = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_root / "inventory_current_duts_001.json"
    approved_md = approved_root / "inventory_current_duts_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None
    retrieval_file = tmp_path / "retrieval.json"
    retrieval_file.write_text(
        json.dumps(
            {
                "retrieval": [
                    {
                        "command": "python3 -m ael inventory list",
                        "returncode": 0,
                        "stdout": "{\"ok\": true}",
                        "stderr": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    try:
        approved_root.mkdir(parents=True, exist_ok=True)
        reference_answer = "Reference baseline answer"
        approved_json.write_text(
            json.dumps(
                {
                    "case": {"case_id": "inventory_current_duts_001"},
                    "question": "What DUTs and tests do we currently have?",
                    "approved_answer_draft": reference_answer,
                    "status": "approved",
                }
            ),
            encoding="utf-8",
        )
        approved_md.write_text(reference_answer, encoding="utf-8")
        out_dir = tmp_path / "retrieval_file_compare"
        res = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                "tests/ai_behavior_cases/organic_cases.yaml",
                "inventory_current_duts_001",
                "--answer-text",
                reference_answer,
                "--retrieval-file",
                str(retrieval_file),
                "--judge-cmd",
                f"{sys.executable} tools/reference_semantic_judge.py",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "retrieval_status: completed" in res.stdout
        assert "verdict: PASS" in res.stdout
        payload = json.loads((out_dir / "inventory_current_duts_001.compare.json").read_text(encoding="utf-8"))
        assert payload["retrieval"][0]["command"] == "python3 -m ael inventory list"
        assert payload["comparison"]["verdict"] == "PASS"
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_reference_compare_stops_when_retrieval_fails(tmp_path):
    case_file = tmp_path / "failing_cases.yaml"
    case_file.write_text(
        yaml.safe_dump(
            [
                {
                    "case_id": "failing_case_001",
                    "case_type": "organic",
                    "intent_type": "inventory_question",
                    "user_question": "failing retrieval case",
                    "expected_retrieval_path": ["python3 -c \"import sys; sys.exit(7)\""],
                    "required_output_elements": ["anything"],
                    "forbidden_failure_modes": [],
                    "judge_rubric": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    approved_dir = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_dir / "failing_case_001.json"
    approved_md = approved_dir / "failing_case_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None
    judge_script = _write_script(
        tmp_path / "should_not_run_judge.py",
        "raise SystemExit('judge should not run')\n",
    )
    try:
        approved_dir.mkdir(parents=True, exist_ok=True)
        approved_json.write_text(
            json.dumps(
                {
                    "case": {"case_id": "failing_case_001"},
                    "question": "failing retrieval case",
                    "approved_answer_draft": "baseline",
                    "status": "approved",
                }
            ),
            encoding="utf-8",
        )
        approved_md.write_text("baseline", encoding="utf-8")
        out_dir = tmp_path / "failing_compare"
        res = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                str(case_file),
                "failing_case_001",
                "--answer-text",
                "fresh answer",
                "--judge-cmd",
                f"{sys.executable} {judge_script}",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=False,
        )
        assert "verdict: ERROR" in res.stdout
        assert "retrieval stage failed; compare was not executed" in res.stdout
        payload = json.loads((out_dir / "failing_case_001.compare.json").read_text(encoding="utf-8"))
        assert payload["comparison"]["verdict_source"] == "retrieval_failure"
        assert payload["comparison"]["mode"] == "retrieval_gate"
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_reference_compare_builtin_semantic_judge_gives_pass_on_exact_match(tmp_path):
    approved_root = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_root / "inventory_current_duts_001.json"
    approved_md = approved_root / "inventory_current_duts_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None
    try:
        approved_root.mkdir(parents=True, exist_ok=True)
        reference_answer = "Reference baseline answer"
        approved_json.write_text(
            json.dumps(
                {
                    "case": {"case_id": "inventory_current_duts_001"},
                    "question": "What DUTs and tests do we currently have?",
                    "approved_answer_draft": reference_answer,
                    "status": "approved",
                }
            ),
            encoding="utf-8",
        )
        approved_md.write_text(reference_answer, encoding="utf-8")
        out_dir = tmp_path / "builtin_judge_compare"
        res = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                "tests/ai_behavior_cases/organic_cases.yaml",
                "inventory_current_duts_001",
                "--answer-text",
                reference_answer,
                "--judge-cmd",
                f"{sys.executable} tools/reference_semantic_judge.py",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "retrieval_status: completed" in res.stdout
        assert "verdict: PASS" in res.stdout
        payload = json.loads((out_dir / "inventory_current_duts_001.compare.json").read_text(encoding="utf-8"))
        assert payload["comparison"]["verdict"] == "PASS"
        assert payload["comparison"]["verdict_source"] == "semantic_judge"
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_reference_compare_allows_guarded_retrieval_failure_when_case_opted_in(tmp_path):
    case_file = tmp_path / "cases.yaml"
    case_file.write_text(
        json.dumps(
            [
                {
                    "case_id": "guarded_failure_case_001",
                    "case_type": "organic",
                    "intent_type": "default_verification_review",
                    "user_question": "What is currently covered and is the default verification baseline healthy?",
                    "expected_retrieval_path": [
                        "python3 -c \"print('inventory ok')\"",
                        "python3 -c \"import sys; print('meter unreachable'); sys.exit(2)\"",
                    ],
                    "allow_retrieval_failure": True,
                    "required_output_elements": [
                        "baseline health assessment",
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    approved_root = REPO_ROOT / "tests" / "ai_behavior_cases" / "references" / "approved"
    approved_json = approved_root / "guarded_failure_case_001.json"
    approved_md = approved_root / "guarded_failure_case_001.md"
    old_json = approved_json.read_text(encoding="utf-8") if approved_json.exists() else None
    old_md = approved_md.read_text(encoding="utf-8") if approved_md.exists() else None
    try:
        approved_root.mkdir(parents=True, exist_ok=True)
        reference_answer = "baseline health assessment: not healthy because the meter is unreachable"
        approved_json.write_text(
            json.dumps(
                {
                    "case": {"case_id": "guarded_failure_case_001"},
                    "question": "What is currently covered and is the default verification baseline healthy?",
                    "approved_answer_draft": reference_answer,
                    "status": "approved",
                }
            ),
            encoding="utf-8",
        )
        approved_md.write_text(reference_answer, encoding="utf-8")
        out_dir = tmp_path / "guarded_failure_compare"
        res = subprocess.run(
            [
                sys.executable,
                "tools/ai_behavior_reference.py",
                "compare",
                str(case_file),
                "guarded_failure_case_001",
                "--answer-text",
                reference_answer,
                "--judge-cmd",
                f"{sys.executable} tools/reference_semantic_judge.py",
                "--output-dir",
                str(out_dir),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=_env(),
            check=True,
        )
        assert "retrieval_status: completed_with_allowed_failures" in res.stdout
        assert "verdict: PASS" in res.stdout
        payload = json.loads((out_dir / "guarded_failure_case_001.compare.json").read_text(encoding="utf-8"))
        assert payload["comparison"]["verdict"] == "PASS"
        assert payload["comparison"]["verdict_source"] == "semantic_judge"
        assert payload["comparison"]["judge_output"]["grounded_in_retrieval"] is True
    finally:
        if old_json is None:
            approved_json.unlink(missing_ok=True)
        else:
            approved_json.write_text(old_json, encoding="utf-8")
        if old_md is None:
            approved_md.unlink(missing_ok=True)
        else:
            approved_md.write_text(old_md, encoding="utf-8")


def test_run_command_retries_transient_hardware_access_failure(monkeypatch):
    import tools.run_ai_behavior_case as runner

    calls = []

    class Result:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, cwd, shell, capture_output, text):
        calls.append(command)
        if len(calls) == 1:
            return Result(4, "Could not open /dev/ttyACM0", "Permission denied: '/dev/ttyACM0'")
        return Result(0, '{"ok": true}', "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.time, "sleep", lambda _s: None)

    result = runner._run_command("python3 -m ael verify-default run")
    assert result["returncode"] == 0
    assert result["retried"] is True
    assert result["attempt_count"] == 2
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["returncode"] == 4
    assert result["attempts"][1]["returncode"] == 0
