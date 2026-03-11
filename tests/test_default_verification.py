import json
import time
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ael import default_verification
from ael.verification_model import VerificationTask, VerificationWorker


def test_worker_logs_failure_summary_details():
    lines = []

    worker = VerificationWorker(
        task=VerificationTask(name="esp32c6_golden_gpio", board="esp32c6_devkit"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=lambda *_args: (
            2,
            {
                "ok": False,
                "error": "meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed.",
                "observations": {
                    "failure_class": "network_meter_api",
                    "ping": {"ok": True},
                    "tcp": {"ok": True},
                    "api": {"ok": False},
                },
            },
        ),
        log_fn=lines.append,
    )

    result = worker.run()

    assert result.ok is False
    fail_line = next(item for item in lines if item.startswith("[FAIL]"))
    assert "failure_class=network_meter_api" in fail_line
    assert "error=meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed." in fail_line
    assert "observations=ping=ok,tcp=ok,api=fail" in fail_line


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
        side_effect=default_verification.instrument_provision.MeterReachabilityError(
            "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. "
            "Suggestion: add a meter reset feature.",
            details={
                "failure_class": "network_meter_reachability",
                "host": "192.168.4.1",
                "port": 9000,
                "ping": {"ok": False},
            },
        ),
    ) as guard_mock, patch("ael.default_verification.run_pipeline") as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 2
    assert result["ok"] is False
    assert result["error"] == (
        "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. Suggestion: add a meter reset feature."
    )
    assert result["observations"]["failure_class"] == "network_meter_reachability"
    assert result["observations"]["host"] == "192.168.4.1"
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


def test_run_single_uses_control_instrument_alias_when_present(tmp_path):
    boards = tmp_path / "configs" / "boards"
    boards.mkdir(parents=True)
    (boards / "alias_board.yaml").write_text(
        """board:
  control_instrument_instance: esp32jtag_rp2040_lab
  control_instrument_required: true
""",
        encoding="utf-8",
    )
    inst_dir = tmp_path / "configs" / "instrument_instances"
    inst_dir.mkdir(parents=True)
    (inst_dir / "esp32jtag_rp2040_lab.yaml").write_text(
        """instance:
  id: esp32jtag_rp2040_lab
  type: esp32jtag
connection:
  ip: 192.168.2.63
  gdb_port: 4242
""",
        encoding="utf-8",
    )
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "alias_board", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 0
    assert result == {"ok": True}
    guard_mock.assert_not_called()
    assert run_mock.call_args.kwargs["probe_path"].endswith("configs/instrument_instances/esp32jtag_rp2040_lab.yaml")


def test_run_single_uses_no_probe_for_esp32c6_meter_path(tmp_path):
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

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ) as run_mock:
        code, result = default_verification._run_single(REPO_ROOT, step, "normal")

    assert code == 0
    assert result == {"ok": True}
    guard_mock.assert_called_once()
    assert run_mock.call_args.kwargs["probe_path"] is None


def test_run_single_keeps_meter_instrument_path_for_esp32c6(tmp_path):
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

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ):
        code, result = default_verification._run_single(REPO_ROOT, step, "normal")

    assert code == 0
    assert result == {"ok": True}
    guard_mock.assert_called_once()
    assert guard_mock.call_args.kwargs["host"] == "192.168.4.1"
    assert guard_mock.call_args.kwargs["manifest"]["id"] == "esp32s3_dev_c_meter"


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


def test_task_resource_keys_include_explicit_probe_and_instrument(tmp_path):
    test_path = tmp_path / "esp32c6_gpio_signature_with_meter.json"
    test_path.write_text(
        json.dumps(
            {
                "name": "esp32c6_gpio_signature_with_meter",
                "instrument": {
                    "id": "esp32s3_dev_c_meter",
                    "tcp": {"host": "192.168.4.1", "port": 9000},
                },
                "bench_setup": {
                    "dut_to_instrument": [{"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle"}],
                    "ground_required": True,
                    "ground_confirmed": True,
                },
            }
        ),
        encoding="utf-8",
    )
    task = VerificationTask(
        name="esp32c6",
        board="esp32c6_devkit",
        config={"test": str(test_path), "probe": "configs/esp32jtag.yaml"},
    )

    keys = default_verification._task_resource_keys(REPO_ROOT, task)

    assert "dut:esp32c6_devkit" in keys
    assert any(key.endswith("/configs/esp32jtag.yaml") for key in keys)
    assert "instrument:esp32s3_dev_c_meter:192.168.4.1:9000" in keys


def test_task_resource_keys_for_esp32c6_default_do_not_include_probe(tmp_path):
    test_path = tmp_path / "esp32c6_gpio_signature_with_meter.json"
    test_path.write_text(
        json.dumps(
            {
                "name": "esp32c6_gpio_signature_with_meter",
                "instrument": {
                    "id": "esp32s3_dev_c_meter",
                    "tcp": {"host": "192.168.4.1", "port": 9000},
                },
                "bench_setup": {
                    "dut_to_instrument": [{"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle"}],
                    "ground_required": True,
                    "ground_confirmed": True,
                },
            }
        ),
        encoding="utf-8",
    )
    task = VerificationTask(
        name="esp32c6",
        board="esp32c6_devkit",
        config={"test": str(test_path)},
    )

    keys = default_verification._task_resource_keys(REPO_ROOT, task)

    assert "dut:esp32c6_devkit" in keys
    assert "instrument:esp32s3_dev_c_meter:192.168.4.1:9000" in keys
    assert not any(key.startswith("probe:") or key.startswith("probe_path:") for key in keys)


def test_worker_claims_shared_resources_serially():
    events = []
    lock = threading.Lock()

    def runner(repo_root, step, output_mode):
        with lock:
            events.append(("start", step["name"], time.monotonic()))
        time.sleep(0.05)
        with lock:
            events.append(("end", step["name"], time.monotonic()))
        return 0, {"ok": True}

    task_a = VerificationTask(name="a", board="board_a")
    task_b = VerificationTask(name="b", board="board_b")
    worker_a = VerificationWorker(task=task_a, repo_root=REPO_ROOT, output_mode="normal", runner=runner, resource_keys=["probe:shared"])
    worker_b = VerificationWorker(task=task_b, repo_root=REPO_ROOT, output_mode="normal", runner=runner, resource_keys=["probe:shared"])

    t1 = threading.Thread(target=worker_a.run)
    t2 = threading.Thread(target=worker_b.run)
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert not t1.is_alive()
    assert not t2.is_alive()
    starts = {name: ts for kind, name, ts in events if kind == "start"}
    ends = {name: ts for kind, name, ts in events if kind == "end"}
    assert ends["a"] <= starts["b"] or ends["b"] <= starts["a"]


def test_worker_with_distinct_resources_can_overlap():
    events = []
    lock = threading.Lock()

    def runner(repo_root, step, output_mode):
        with lock:
            events.append(("start", step["name"], time.monotonic()))
        time.sleep(0.05)
        with lock:
            events.append(("end", step["name"], time.monotonic()))
        return 0, {"ok": True}

    task_a = VerificationTask(name="a", board="board_a")
    task_b = VerificationTask(name="b", board="board_b")
    worker_a = VerificationWorker(task=task_a, repo_root=REPO_ROOT, output_mode="normal", runner=runner, resource_keys=["probe:a"])
    worker_b = VerificationWorker(task=task_b, repo_root=REPO_ROOT, output_mode="normal", runner=runner, resource_keys=["probe:b"])

    t1 = threading.Thread(target=worker_a.run)
    t2 = threading.Thread(target=worker_b.run)
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert not t1.is_alive()
    assert not t2.is_alive()
    starts = {name: ts for kind, name, ts in events if kind == "start"}
    ends = {name: ts for kind, name, ts in events if kind == "end"}
    assert starts["a"] < ends["b"]
    assert starts["b"] < ends["a"]


def test_worker_holds_shared_lock_for_full_repeat_window():
    events = []
    lock = threading.Lock()

    def runner(repo_root, step, output_mode):
        iteration = sum(1 for kind, name, *_rest in events if kind == "start" and name == step["name"]) + 1
        with lock:
            events.append(("start", step["name"], iteration, time.monotonic()))
        time.sleep(0.03)
        with lock:
            events.append(("end", step["name"], iteration, time.monotonic()))
        return 0, {"ok": True}

    worker_a = VerificationWorker(
        task=VerificationTask(name="a", board="board_a"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=runner,
        iteration_limit=2,
        resource_keys=["probe:shared"],
    )
    worker_b = VerificationWorker(
        task=VerificationTask(name="b", board="board_b"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=runner,
        iteration_limit=1,
        resource_keys=["probe:shared"],
    )

    t1 = threading.Thread(target=worker_a.run)
    t2 = threading.Thread(target=worker_b.run)
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert not t1.is_alive()
    assert not t2.is_alive()
    a_end_second = next(ts for kind, name, iteration, ts in events if kind == "end" and name == "a" and iteration == 2)
    b_start = next(ts for kind, name, iteration, ts in events if kind == "start" and name == "b")
    assert a_end_second <= b_start


def test_parallel_suite_waits_for_other_workers_after_one_failure(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"name": "fast_fail", "board": "rp2040_pico", "test": "tests/plans/gpio_signature.json"},
            {"name": "slow_pass", "board": "stm32f103", "test": "tests/plans/gpio_signature.json"},
        ],
    }

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        def _run():
            if task.name == "fast_fail":
                time.sleep(0.01)
                payload = {
                    "name": task.name,
                    "board": task.board,
                    "requested_iterations": 1,
                    "completed_iterations": 1,
                    "pass_count": 0,
                    "fail_count": 1,
                    "ok": False,
                    "results": [
                        {"name": task.name, "board": task.board, "iteration": 1, "code": 7, "ok": False, "result": {"error": "failed early"}}
                    ],
                }
            else:
                time.sleep(0.05)
                payload = {
                    "name": task.name,
                    "board": task.board,
                    "requested_iterations": 1,
                    "completed_iterations": 1,
                    "pass_count": 1,
                    "fail_count": 0,
                    "ok": True,
                    "results": [
                        {"name": task.name, "board": task.board, "iteration": 1, "code": 0, "ok": True, "result": {"ok": True}}
                    ],
                }
            return SimpleNamespace(to_dict=lambda: payload)

        return SimpleNamespace(run=_run)

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_default_setting(path=_write_setting(tmp_path, setting))

    assert code == 7
    assert payload["ok"] is False
    by_name = {worker["name"]: worker for worker in payload["workers"]}
    assert by_name["fast_fail"]["fail_count"] == 1
    assert by_name["slow_pass"]["pass_count"] == 1
    assert len(payload["results"]) == 2
    assert any(item["name"] == "slow_pass" and item["ok"] for item in payload["results"])


def test_print_worker_totals_includes_failure_details(capsys):
    lock = threading.Lock()
    workers = [
        {
            "name": "esp32c6_golden_gpio",
            "completed_iterations": 1,
            "pass_count": 0,
            "ok": False,
            "results": [
                {
                    "result": {
                        "error": "meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed.",
                        "observations": {
                            "failure_class": "network_meter_api",
                            "ping": {"ok": True},
                            "tcp": {"ok": True},
                            "api": {"ok": False},
                        },
                    }
                }
            ],
        }
    ]

    default_verification._print_worker_totals(lock, workers)
    out = capsys.readouterr().out

    assert "[SUMMARY]" in out
    assert "esp32c6_golden_gpio: 0/1 PASS" in out
    assert "failure_class=network_meter_api" in out
    assert "error=meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed." in out
    assert "observations=ping=ok,tcp=ok,api=fail" in out
