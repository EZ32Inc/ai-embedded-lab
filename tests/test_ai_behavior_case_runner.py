import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runner_emits_json_bundle_for_inventory_case(tmp_path):
    out_json = tmp_path / "case_result.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "inventory_current_duts_001",
            "--write-json",
            str(out_json),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "case_id: inventory_current_duts_001" in res.stdout
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["case"]["case_id"] == "inventory_current_duts_001"
    assert payload["retrieval"][0]["command"] == "python3 -m ael inventory list"
    assert payload["retrieval"][0]["returncode"] == 0
    assert payload["automation"]["answer_generation"] == "prompt_assisted"


def test_runner_can_print_answer_prompt():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "tools/run_ai_behavior_case.py",
            "tests/ai_behavior_cases/organic_cases.yaml",
            "describe_test_stm32f401_001",
            "--print-answer-prompt",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "---ANSWER_PROMPT---" in res.stdout
    assert "Please show me stm32f401rct6 golden GPIO test connections" in res.stdout
    assert "python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/gpio_signature.json" in res.stdout
