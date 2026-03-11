import json
import os
import subprocess
import sys
from pathlib import Path

from ael import pipeline


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_workflow_archive_records_plan_run(monkeypatch, tmp_path):
    monkeypatch.setenv("AEL_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("AEL_WORKFLOW_ARCHIVE_ROOT", str(tmp_path / "workflow_archive"))
    monkeypatch.setenv("AEL_SESSION_ID", "sess-123")
    monkeypatch.setenv("AEL_TASK_ID", "task-123")
    monkeypatch.setenv("AEL_USER_REQUEST", "Add a new ESP32-C3 board and run plan.")
    monkeypatch.setenv("AEL_AI_RESPONSE", "Creating the board path and running plan.")
    monkeypatch.setenv("AEL_USER_CONFIRMATION", "Use the ESP32-S3 GPIO meter assumptions for now.")
    monkeypatch.setenv("AEL_AI_NEXT_ACTION", "Run the plan stage for the new board.")

    code, run_paths = pipeline.run_pipeline(
        probe_path="configs/esp32jtag.yaml",
        board_arg="esp32c3_devkit",
        test_path="tests/plans/esp32c3_gpio_signature_with_meter.json",
        output_mode="quiet",
        until_stage="plan",
        return_paths=True,
    )

    assert code == 0

    global_archive = tmp_path / "workflow_archive" / "events.jsonl"
    run_archive = run_paths.root / "workflow_events.jsonl"

    assert global_archive.exists()
    assert run_archive.exists()

    records = _read_jsonl(global_archive)
    assert [(r["category"], r["actor"], r["action"]) for r in records] == [
        ("runtime", "ael", "run_started"),
        ("workflow", "user", "request"),
        ("workflow", "assistant", "response"),
        ("workflow", "user", "confirmation"),
        ("workflow", "assistant", "next_action"),
        ("runtime", "ael", "run_finished"),
    ]

    finished = records[-1]
    assert finished["run_id"] == run_paths.run_id
    assert finished["session_id"] == "sess-123"
    assert finished["selected_dut"]["id"] == "esp32c3_devkit"
    assert finished["selected_board_profile"]["config"].endswith("configs/boards/esp32c3_devkit.yaml")
    assert finished["selected_bench_resources"]["instrument"]["id"] == "esp32s3_dev_c_meter"
    assert finished["test"]["name"] == "esp32c3_gpio_signature_with_meter"
    assert finished["control_instrument"]["communication"]["primary"] == "gdb_remote"
    assert finished["control_instrument"]["capability_surfaces"]["swd"] == "gdb_remote"
    assert finished["selected"]["board_profile_config"].endswith("configs/boards/esp32c3_devkit.yaml")
    assert finished["selected"]["control_instrument_config"].endswith("configs/esp32jtag.yaml")
    assert finished["selected"]["compatibility"]["probe_config"].endswith("configs/esp32jtag.yaml")
    assert finished["compatibility"]["board"]["id"] == "esp32c3_devkit"
    assert finished["compatibility"]["probe"]["communication"]["primary"] == "gdb_remote"
    assert finished["instrument"]["communication"]["protocol"] == "gpio_meter_v1"
    assert finished["instrument"]["capability_surfaces"]["measure.digital"] == "primary"
    assert any(item.startswith("digital X1(GPIO4)->GPIO11") for item in finished["connection_digest"])
    assert finished["stage"] == "plan"
    assert finished["status"] == "completed"
    assert finished["stage_execution"]["executed"] == ["plan", "report"]
    assert "run_plan" in finished["artifacts"]


def test_workflow_archive_show_cli(monkeypatch, tmp_path):
    monkeypatch.setenv("AEL_WORKFLOW_ARCHIVE_ROOT", str(tmp_path / "workflow_archive"))
    monkeypatch.setenv("AEL_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("AEL_USER_REQUEST", "Inspect archive.")

    code, _ = pipeline.run_pipeline(
        probe_path="configs/esp32jtag.yaml",
        board_arg="esp32c3_devkit",
        test_path="tests/plans/esp32c3_gpio_signature_with_meter.json",
        output_mode="quiet",
        until_stage="plan",
        return_paths=True,
    )
    assert code == 0

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["AEL_WORKFLOW_ARCHIVE_ROOT"] = str(tmp_path / "workflow_archive")
    res = subprocess.run(
        [sys.executable, "-m", "ael", "workflow-archive", "show", "--limit", "2"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert len(payload) == 2
    assert payload[-1]["action"] == "run_finished"


def test_pipeline_blocks_unreachable_meter_before_run(monkeypatch, tmp_path):
    monkeypatch.setenv("AEL_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("AEL_WORKFLOW_ARCHIVE_ROOT", str(tmp_path / "workflow_archive"))

    def _fail_meter(*args, **kwargs):
        raise RuntimeError(
            "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. "
            "Suggestion: add a meter reset feature."
        )

    monkeypatch.setattr("ael.pipeline.instrument_provision.ensure_meter_reachable", _fail_meter)

    code, run_paths = pipeline.run_pipeline(
        probe_path="configs/esp32jtag.yaml",
        board_arg="esp32c6_devkit",
        test_path="tests/plans/esp32c6_gpio_signature_with_meter.json",
        output_mode="quiet",
        return_paths=True,
    )

    assert code == 6
    result = json.loads(Path(run_paths.result).read_text(encoding="utf-8"))
    assert result["ok"] is False
    assert result["failed_step"] == "check_meter_reachability"
    assert "manual checking" in result["error_summary"]

    records = _read_jsonl(run_paths.root / "workflow_events.jsonl")
    assert records[-1]["action"] == "run_finished"
    assert records[-1]["status"] == "failed"
    assert records[-1]["result"]["failed_step"] == "check_meter_reachability"


def test_workflow_archive_demotes_legacy_probe_fields_under_compatibility(monkeypatch, tmp_path):
    monkeypatch.setenv("AEL_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("AEL_WORKFLOW_ARCHIVE_ROOT", str(tmp_path / "workflow_archive"))

    code, run_paths = pipeline.run_pipeline(
        probe_path="configs/esp32jtag.yaml",
        board_arg="esp32c3_devkit",
        test_path="tests/plans/esp32c3_gpio_signature_with_meter.json",
        output_mode="quiet",
        until_stage="plan",
        return_paths=True,
    )

    assert code == 0

    records = _read_jsonl(run_paths.root / "workflow_events.jsonl")
    finished = records[-1]
    assert "probe" not in finished
    assert "board" not in finished
    assert finished["compatibility"]["probe"]["path"].endswith("configs/esp32jtag.yaml")
    assert finished["compatibility"]["board"]["id"] == "esp32c3_devkit"
