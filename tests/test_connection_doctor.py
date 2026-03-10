from pathlib import Path
import json
import os
import subprocess
import sys

from ael import connection_doctor


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_connection_doctor_for_meter_path_reports_clean_conn_a():
    payload = connection_doctor.doctor(
        board_id="esp32c6_devkit",
        test_path="tests/plans/esp32c6_gpio_signature_with_meter.json",
        repo_root=REPO_ROOT,
    )
    assert payload["ok"] is True
    assert payload["validation_errors"] == []
    assert payload["source_summary"]["bench_setup"] == "test.bench_setup"
    assert any(item["name"] == "ground_confirmation" and item["ok"] is True for item in payload["consistency_checks"])


def test_connection_doctor_for_stm32_path_surfaces_duplicate_observation_warning():
    payload = connection_doctor.doctor(
        board_id="stm32f401rct6",
        test_path="tests/plans/gpio_signature.json",
        repo_root=REPO_ROOT,
    )
    assert payload["ok"] is True
    assert any("PC13 is connected to 2 observation points" in item for item in payload["warnings"])
    assert any(item["name"] == "duplicate_observation_points" and item["ok"] is False for item in payload["consistency_checks"])


def test_connection_doctor_cli_json_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "connection", "doctor", "--board", "esp32c6_devkit", "--test", "tests/plans/esp32c6_gpio_signature_with_meter.json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["validation_errors"] == []
