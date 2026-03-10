import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ael import default_verification


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_setting(tmp_path, payload):
    path = tmp_path / "default_verification_setting.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_run_single_blocks_unreachable_esp32_meter(tmp_path):
    test_path = tmp_path / "esp32c6_gpio_signature_with_meter.json"
    test_path.write_text(
        """{
  "name": "esp32c6_gpio_signature_with_meter",
  "instrument": {
    "id": "esp32s3_dev_c_meter",
    "tcp": {
      "host": "192.168.4.1",
      "port": 9000
    }
  },
  "bench_setup": {
    "dut_to_instrument": [
      {
        "dut_gpio": "X1(GPIO4)",
        "inst_gpio": 11,
        "expect": "toggle"
      }
    ]
  }
}""",
        encoding="utf-8",
    )
    step = {"board": "esp32c6_devkit", "test": str(test_path)}

    with patch(
        "ael.default_verification.instrument_provision.ensure_meter_reachable",
        side_effect=RuntimeError(
            "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. "
            "Suggestion: add a meter reset feature."
        ),
    ) as guard_mock, patch("ael.default_verification.run_pipeline") as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 2
    assert result == {
        "ok": False,
        "error": "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. Suggestion: add a meter reset feature.",
    }
    guard_mock.assert_called_once()
    run_mock.assert_not_called()


def test_run_single_skips_meter_guard_for_non_meter_test(tmp_path):
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "rp2040_pico", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 0
    assert result == {"ok": True}
    guard_mock.assert_not_called()
    run_mock.assert_called_once()


def test_run_single_uses_board_probe_default_when_step_probe_missing(tmp_path):
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "rp2040_pico", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ) as run_mock:
        code, result = default_verification._run_single(REPO_ROOT, step, "normal")

    assert code == 0
    assert result == {"ok": True}
    guard_mock.assert_not_called()
    assert run_mock.call_args.kwargs["probe_path"].endswith("configs/instrument_instances/esp32jtag_rp2040_lab.yaml")


def test_run_until_fail_stops_on_first_failure(tmp_path):
    cfg_path = _write_setting(
        tmp_path,
        {
            "version": 1,
            "mode": "sequence",
            "execution_policy": {"kind": "serial"},
            "steps": [{"name": "dummy", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"}],
        },
    )
    calls = [
        (0, {"ok": True, "mode": "sequence", "results": [{"name": "ok_step", "code": 0, "ok": True, "result": {"ok": True}}]}),
        (
            6,
            {
                "ok": False,
                "mode": "sequence",
                "results": [
                    {"name": "esp32c6_golden_gpio", "code": 0, "ok": True, "result": {"ok": True}},
                    {
                        "name": "stm32f103_golden_gpio_signature",
                        "code": 6,
                        "ok": False,
                        "result": {"ok": False, "error": "edges=0 on verify"},
                    },
                ],
            },
        ),
    ]

    with patch("ael.default_verification.run_default_setting", side_effect=calls):
        code, payload = default_verification.run_until_fail(limit=10, path=cfg_path)

    assert code == 6
    assert payload["ok"] is False
    assert payload["completed_runs"] == 2
    assert payload["failure"] == {
        "code": 6,
        "step_name": "stm32f103_golden_gpio_signature",
        "step_code": 6,
        "reason": "edges=0 on verify",
    }
    assert len(payload["runs"]) == 2


def test_run_until_fail_reports_success_when_all_runs_pass(tmp_path):
    cfg_path = _write_setting(
        tmp_path,
        {
            "version": 1,
            "mode": "sequence",
            "execution_policy": {"kind": "serial"},
            "steps": [{"name": "dummy", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"}],
        },
    )
    with patch(
        "ael.default_verification.run_default_setting",
        side_effect=[
            (0, {"ok": True, "mode": "sequence", "results": []}),
            (0, {"ok": True, "mode": "sequence", "results": []}),
            (0, {"ok": True, "mode": "sequence", "results": []}),
        ],
    ):
        code, payload = default_verification.run_until_fail(limit=3, path=cfg_path)

    assert code == 0
    assert payload["ok"] is True
    assert payload["completed_runs"] == 3
    assert len(payload["runs"]) == 3


def test_parallel_sequence_run_uses_worker_summaries(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"name": "rp2040", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"},
            {"name": "stm32", "board": "stm32f103", "test": "tests/plans/gpio_signature.json"},
        ],
    }

    with patch(
        "ael.default_verification._run_step_action",
        side_effect=[
            (0, {"ok": True}),
            (6, {"ok": False, "error": "verify failed"}),
        ],
    ):
        code, payload = default_verification.run_default_setting(path=_write_setting(tmp_path, setting))

    assert code == 6
    assert payload["execution_policy"] == {"kind": "parallel", "iterations_per_worker": 1}
    assert len(payload["workers"]) == 2
    assert len(payload["results"]) == 2
    assert any(not item["ok"] for item in payload["results"])


def test_sequence_setting_materializes_suite_and_tasks():
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"name": "rp2040", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"},
            {"name": "stm32", "board": "stm32f103", "test": "tests/plans/gpio_signature.json"},
        ],
    }

    suite = default_verification._suite_from_setting(setting)

    assert suite.name == "default_verification"
    assert suite.execution_policy["kind"] == "parallel"
    assert [task.name for task in suite.tasks] == ["rp2040", "stm32"]
    assert [task.board for task in suite.tasks] == ["rp2040_pico", "stm32f103"]


def test_parallel_repeat_until_fail_is_per_worker(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"name": "rp2040", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"},
            {"name": "esp32", "board": "esp32c6_devkit", "test": "tests/plans/esp32c6_gpio_signature_with_meter.json"},
        ],
    }
    cfg_path = _write_setting(tmp_path, setting)

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        if task.name == "rp2040":
            payload = {
                "name": "rp2040",
                "board": "rp2040_pico",
                "requested_iterations": max_iterations,
                "completed_iterations": 3,
                "pass_count": 2,
                "fail_count": 1,
                "ok": False,
                "results": [
                    {"name": "rp2040", "board": "rp2040_pico", "iteration": 1, "code": 0, "ok": True, "result": {"ok": True}},
                    {"name": "rp2040", "board": "rp2040_pico", "iteration": 2, "code": 0, "ok": True, "result": {"ok": True}},
                    {"name": "rp2040", "board": "rp2040_pico", "iteration": 3, "code": 9, "ok": False, "result": {"error": "rp2040 fail"}},
                ],
            }
        else:
            payload = {
                "name": "esp32",
                "board": "esp32c6_devkit",
                "requested_iterations": max_iterations,
                "completed_iterations": 5,
                "pass_count": 5,
                "fail_count": 0,
                "ok": True,
                "results": [
                    {"name": "esp32", "board": "esp32c6_devkit", "iteration": i, "code": 0, "ok": True, "result": {"ok": True}}
                    for i in range(1, 6)
                ],
            }
        return SimpleNamespace(run=lambda: SimpleNamespace(to_dict=lambda: payload))

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_until_fail(limit=5, path=cfg_path)

    assert code == 9
    assert payload["requested_iterations_per_worker"] == 5
    by_name = {worker["name"]: worker for worker in payload["workers"]}
    assert by_name["rp2040"]["completed_iterations"] == 3
    assert by_name["esp32"]["completed_iterations"] == 5
    assert payload["failure"]["step_name"] == "rp2040"
    assert payload["failure"]["iteration"] == 3
