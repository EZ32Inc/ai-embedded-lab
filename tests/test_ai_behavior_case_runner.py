import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _env():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    return env


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
