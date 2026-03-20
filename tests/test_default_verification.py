import json
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ael.__main__ import _render_verify_default_review_text, _render_verify_default_state_text, _verify_default_state
from ael_controlplane.nightly import NightlyConfig, run_nightly
from ael_controlplane.nightly_report import build_nightly_report_payload, write_nightly_report
from ael_controlplane.reporting import default_verification_review_highlights, default_verification_review_payload
from ael_controlplane.review_pack import build_review_pack_payload, generate_review_pack
from ael import default_verification
from ael.verification_model import VerificationTask, VerificationWorker, summarize_resource_keys
from tools.audit_test_plan_schema import build_report


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
    assert "instrument_condition=instrument_api_unavailable" in fail_line
    assert "failure_scope=bench" in fail_line
    assert "policy_class=bench_degraded_retry_once" in fail_line
    assert "error=meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed." in fail_line
    assert "observations=ping=ok,tcp=ok,api=fail" in fail_line


def test_worker_logs_wait_when_blocked_on_shared_resource():
    first_lines = []
    second_lines = []
    release = threading.Event()

    def first_runner(*_args):
        release.wait(timeout=1.0)
        return 0, {"ok": True}

    def second_runner(*_args):
        return 0, {"ok": True}

    worker_a = VerificationWorker(
        task=VerificationTask(name="esp32c6_golden_gpio", board="esp32c6_devkit"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=first_runner,
        log_fn=first_lines.append,
        resource_keys=["instrument:esp32s3_dev_c_meter:192.168.4.1:9000"],
    )
    worker_b = VerificationWorker(
        task=VerificationTask(name="stm32f103_golden_gpio_signature", board="stm32f103"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=second_runner,
        log_fn=second_lines.append,
        resource_keys=["instrument:esp32s3_dev_c_meter:192.168.4.1:9000"],
    )

    t1 = threading.Thread(target=worker_a.run)
    t2 = threading.Thread(target=worker_b.run)
    t1.start()
    time.sleep(0.05)
    t2.start()
    time.sleep(0.1)
    release.set()
    t1.join(timeout=1.0)
    t2.join(timeout=1.0)

    wait_line = next(item for item in second_lines if item.startswith("[WAIT]"))
    assert "stm32f103_golden_gpio_signature waiting for resource instrument:esp32s3_dev_c_meter:192.168.4.1:9000" in wait_line


def test_worker_result_includes_resource_keys_and_summary():
    worker = VerificationWorker(
        task=VerificationTask(name="rp2040_golden_gpio_signature", board="rp2040_pico"),
        repo_root=REPO_ROOT,
        output_mode="normal",
        runner=lambda *_args: (0, {"ok": True}),
        resource_keys=[
            "dut:rp2040_pico",
            "probe:192.168.2.63:4242",
            "serial:/dev/ttyACM0",
            "instrument:esp32s3_dev_c_meter:192.168.4.1:9000",
        ],
    )

    payload = worker.run().to_dict()

    assert payload["resource_keys"] == [
        "dut:rp2040_pico",
        "probe:192.168.2.63:4242",
        "serial:/dev/ttyACM0",
        "instrument:esp32s3_dev_c_meter:192.168.4.1:9000",
    ]
    assert payload["resource_summary"]["dut_ids"] == ["rp2040_pico"]
    assert payload["resource_summary"]["control_instrument_endpoints"] == ["192.168.2.63:4242"]
    assert payload["resource_summary"]["serial_ports"] == ["/dev/ttyACM0"]
    assert payload["resource_summary"]["instrument_endpoints"] == ["esp32s3_dev_c_meter:192.168.4.1:9000"]


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
    assert result["error_summary"] == result["error"]
    assert result["failure_class"] == "network_meter_reachability"
    assert result["failure_scope"] == "bench"
    assert result["degraded_instrument_policy"]["policy_class"] == "bench_degraded_fail_fast"
    assert result["observations"]["failure_class"] == "network_meter_reachability"
    assert result["observations"]["instrument_condition"] == "instrument_unreachable"
    assert result["observations"]["failure_scope"] == "bench"
    assert result["observations"]["host"] == "192.168.4.1"
    assert result["retry_summary"]["meter_guard_attempts"] == 1
    guard_mock.assert_called_once()
    assert guard_mock.call_args.kwargs["timeout_s"] == default_verification.instrument_provision.RUN_METER_GUARD_TIMEOUT_S
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
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "jtag_native_api"
    guard_mock.assert_not_called()
    run_mock.assert_called_once()


def test_run_single_surfaces_schema_advisories_for_structured_meter_path(tmp_path):
    test_path = tmp_path / "meter_path.json"
    test_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "meter_path",
                "test_kind": "instrument_specific",
                "board": "esp32c6_devkit",
                "supported_instruments": ["esp32_meter"],
                "requires": {"mailbox": False, "datacapture": True},
                "labels": ["meter", "instrument_path"],
                "covers": ["gpio", "voltage"],
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
    step = {"board": "esp32c6_devkit", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=(0, {"ok": True}),
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 0
    assert result["ok"] is True
    assert result["plan_schema_kind"] == "structured"
    assert result["test_kind"] == "instrument_specific"
    assert result["supported_instrument_advisory"]["status"] == "declared_supported"
    assert result["schema_advisories"] == [
        "instrument-side measurement path",
        "requires instrument-side measurement and no mailbox dependency",
        "selected instrument type esp32_meter is declared supported",
    ]
    assert result.get("schema_warning_messages") is None or result.get("schema_warning_messages") == []
    guard_mock.assert_called_once()
    run_mock.assert_called_once()


def test_run_single_prints_warning_for_unsupported_declared_instrument(tmp_path, capsys):
    test_path = tmp_path / "unsupported_meter_path.json"
    test_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "unsupported_meter_path",
                "test_kind": "instrument_specific",
                "board": "esp32c6_devkit",
                "supported_instruments": ["stlink"],
                "requires": {"mailbox": False, "datacapture": True},
                "labels": ["meter", "instrument_path"],
                "covers": ["gpio", "voltage"],
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
    step = {"board": "esp32c6_devkit", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=(0, {"ok": True}),
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    captured = capsys.readouterr().out
    assert code == 0
    assert result["supported_instrument_advisory"]["status"] == "declared_unsupported"
    assert result["schema_warning_messages"] == ["selected instrument type esp32_meter is not in declared support set"]
    assert "default_verification: warning - selected instrument type esp32_meter is not in declared support set" in captured
    guard_mock.assert_called_once()
    run_mock.assert_called_once()


def test_run_single_promotes_verify_failure_details_from_pipeline(tmp_path):
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "rp2040_pico", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=(
            6,
            {
                "ok": False,
                "error_summary": "instrument digital verification failed",
                "verify_substage": "instrument.signature",
                "failure_class": "instrument_digital_mismatch",
                "observations": {"missing_expected_channels": ["GPIO11"]},
            },
        ),
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 6
    assert result["ok"] is False
    assert result["error_summary"] == "instrument digital verification failed"
    assert result["verify_substage"] == "instrument.signature"
    assert result["failure_class"] == "instrument_digital_mismatch"
    assert result["instrument_condition"] == "instrument_verify_failed"
    assert result["failure_scope"] == "verify"
    assert result["degraded_instrument_policy"]["policy_class"] == "verify_no_retry"
    assert result["observations"]["missing_expected_channels"] == ["GPIO11"]
    guard_mock.assert_not_called()
    run_mock.assert_called_once()


def test_run_single_reads_verify_result_details_when_pipeline_payload_is_sparse(tmp_path):
    verify_out = tmp_path / "verify_result.json"
    verify_out.write_text(
        json.dumps(
            {
                "error_summary": "instrument digital verification failed",
                "verify_substage": "instrument.signature",
                "failure_class": "instrument_digital_mismatch",
                "missing_expected_channels": ["GPIO11"],
                "mismatch_reasons": ["state_mismatch"],
            }
        ),
        encoding="utf-8",
    )
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "rp2040_pico", "test": str(test_path)}

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=(
            6,
            {
                "ok": False,
                "json": {"verify_result": str(verify_out)},
            },
        ),
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 6
    assert result["ok"] is False
    assert result["error_summary"] == "instrument digital verification failed"
    assert result["verify_substage"] == "instrument.signature"
    assert result["failure_class"] == "instrument_digital_mismatch"
    assert result["instrument_condition"] == "instrument_verify_failed"
    assert result["failure_scope"] == "verify"
    assert result["degraded_instrument_policy"]["policy_class"] == "verify_no_retry"
    assert result["observations"]["missing_expected_channels"] == ["GPIO11"]
    assert result["observations"]["mismatch_reasons"] == ["state_mismatch"]
    guard_mock.assert_not_called()
    run_mock.assert_called_once()


def test_run_single_reads_verify_result_details_when_pipeline_returns_run_paths(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "verify_result.json").write_text(
        json.dumps(
            {
                "error_summary": "instrument digital verification failed",
                "verify_substage": "instrument.signature",
                "failure_class": "instrument_digital_mismatch",
                "missing_expected_channels": ["GPIO11"],
            }
        ),
        encoding="utf-8",
    )
    test_path = tmp_path / "gpio_signature.json"
    test_path.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")
    step = {"board": "rp2040_pico", "test": str(test_path)}
    run_paths = SimpleNamespace(artifacts_dir=artifacts_dir)

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=(6, run_paths),
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 6
    assert result["ok"] is False
    assert result["error_summary"] == "instrument digital verification failed"
    assert result["verify_substage"] == "instrument.signature"
    assert result["failure_class"] == "instrument_digital_mismatch"
    assert result["instrument_condition"] == "instrument_verify_failed"
    assert result["failure_scope"] == "verify"
    assert result["degraded_instrument_policy"]["policy_class"] == "verify_no_retry"
    assert result["observations"]["missing_expected_channels"] == ["GPIO11"]
    guard_mock.assert_not_called()
    run_mock.assert_called_once()


def test_run_single_retries_transient_meter_api_failure_once(tmp_path):
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
    first_error = default_verification.instrument_provision.MeterReachabilityError(
        "meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed.",
        details={
            "failure_class": "network_meter_api",
            "host": "192.168.4.1",
            "port": 9000,
            "ping": {"ok": True},
            "tcp": {"ok": True},
            "api": {"ok": False},
        },
    )

    with patch(
        "ael.default_verification.instrument_provision.ensure_meter_reachable",
        side_effect=[first_error, None],
    ) as guard_mock, patch("ael.default_verification.time.sleep") as sleep_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 0
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "meter_native_api"
    assert guard_mock.call_count == 2
    sleep_mock.assert_called_once_with(1.0)
    run_mock.assert_called_once()


def test_run_single_does_not_retry_unreachable_meter(tmp_path):
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
    error = default_verification.instrument_provision.MeterReachabilityError(
        "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. Suggestion: add a meter reset feature.",
        details={
            "failure_class": "network_meter_reachability",
            "host": "192.168.4.1",
            "port": 9000,
            "ping": {"ok": False},
        },
    )

    with patch(
        "ael.default_verification.instrument_provision.ensure_meter_reachable",
        side_effect=error,
    ) as guard_mock, patch("ael.default_verification.time.sleep") as sleep_mock, patch(
        "ael.default_verification.run_pipeline"
    ) as run_mock:
        code, result = default_verification._run_single(tmp_path, step, "normal")

    assert code == 2
    assert result["degraded_instrument_policy"]["retryable"] is False
    assert result["degraded_instrument_policy"]["policy_class"] == "bench_degraded_fail_fast"
    guard_mock.assert_called_once()
    sleep_mock.assert_not_called()
    run_mock.assert_not_called()


def test_print_worker_totals_reports_degraded_instrument_summary(capsys):
    default_verification._print_worker_totals(
        threading.Lock(),
        [
            {
                "name": "esp32c6_golden_gpio",
                "completed_iterations": 2,
                "pass_count": 1,
                "ok": False,
                "results": [
                    {
                        "result": {
                            "failure_class": "network_meter_api",
                            "instrument_condition": "instrument_api_unavailable",
                        }
                    }
                ],
            },
            {
                "name": "rp2040_golden_gpio_signature",
                "completed_iterations": 2,
                "pass_count": 2,
                "ok": True,
                "results": [{"result": {"ok": True}}],
            },
        ],
    )
    out = capsys.readouterr().out
    assert "[SUMMARY] degraded_instruments instrument_api_unavailable=1" in out


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
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "jtag_native_api"
    guard_mock.assert_not_called()
    assert run_mock.call_args.kwargs["probe_path"] is None


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
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "jtag_native_api"
    guard_mock.assert_not_called()
    assert run_mock.call_args.kwargs["probe_path"] is None


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
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "meter_native_api"
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
    assert result["ok"] is True
    assert result["local_instrument_interface_path"] == "meter_native_api"
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
                "steps": [{"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"}],
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
                "steps": [{"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"}],
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
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
            {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
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
    assert payload["selected_dut_tests"] == ["rp2040_gpio_signature", "stm32f103_gpio_signature"]
    assert len(payload["workers"]) == 2
    assert len(payload["results"]) == 2
    assert any(not item["ok"] for item in payload["results"])


def test_serial_default_verification_prints_selected_dut_tests(tmp_path, capsys):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "serial"},
        "steps": [
            {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
        ],
    }

    with patch("ael.default_verification._run_step_action", return_value=(0, {"ok": True})):
        code, payload = default_verification.run_default_setting(path=_write_setting(tmp_path, setting))

    out = capsys.readouterr().out
    assert code == 0
    assert payload["selected_dut_tests"] == ["stm32f103_gpio_signature"]
    assert "default_verification: selected DUT tests: stm32f103_gpio_signature" in out


def test_serial_default_verification_surfaces_schema_advisory_summary(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "serial"},
        "steps": [
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
            {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
        ],
    }

    with patch(
        "ael.default_verification._run_step_action",
        side_effect=[
            (
                0,
                {
                    "ok": True,
                    "plan_schema_kind": "structured",
                    "test_kind": "instrument_specific",
                    "supported_instrument_advisory": {"status": "declared_supported"},
                    "schema_warning_messages": [],
                },
            ),
            (0, {"ok": True, "plan_schema_kind": "legacy"}),
        ],
    ):
        code, payload = default_verification.run_default_setting(path=_write_setting(tmp_path, setting))

    assert code == 0
    assert payload["schema_advisory_summary"] == {
        "structured_step_count": 1,
        "legacy_step_count": 1,
        "test_kind_counts": {"instrument_specific": 1},
        "supported_instrument_status_counts": {"declared_supported": 1},
        "warning_messages": [],
        "instrument_specific_steps": ["esp32c6_uart_banner"],
    }


def test_serial_default_verification_prints_schema_warning_overview(tmp_path, capsys):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "serial"},
        "steps": [
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
        ],
    }

    with patch(
        "ael.default_verification._run_step_action",
        side_effect=[
            (
                2,
                {
                    "ok": False,
                    "plan_schema_kind": "structured",
                    "test_kind": "instrument_specific",
                    "supported_instrument_advisory": {"status": "declared_unsupported"},
                    "schema_warning_messages": [
                        "selected instrument type esp32_meter is not in declared support set"
                    ],
                },
            ),
            (0, {"ok": True, "plan_schema_kind": "legacy"}),
        ],
    ):
        code, payload = default_verification.run_default_setting(path=_write_setting(tmp_path, setting))

    out = capsys.readouterr().out
    assert code == 2
    assert payload["schema_advisory_summary"]["supported_instrument_status_counts"] == {"declared_unsupported": 1}
    assert "default_verification: schema warnings present" in out
    assert "default_verification: schema warning - selected instrument type esp32_meter is not in declared support set" in out


def test_parallel_repeat_until_fail_surfaces_schema_advisory_summary(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
        ],
    }
    cfg_path = _write_setting(tmp_path, setting)

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        if task.name == "esp32c6_uart_banner":
            payload = {
                "name": task.name,
                "board": task.board,
                "requested_iterations": max_iterations,
                "completed_iterations": 1,
                "pass_count": 0,
                "fail_count": 1,
                "ok": False,
                "results": [
                    {
                        "name": task.name,
                        "board": task.board,
                        "iteration": 1,
                        "code": 2,
                        "ok": False,
                        "result": {
                            "ok": False,
                            "plan_schema_kind": "structured",
                            "test_kind": "instrument_specific",
                            "supported_instrument_advisory": {"status": "declared_unsupported"},
                            "schema_warning_messages": [
                                "selected instrument type esp32_meter is not in declared support set"
                            ],
                        },
                    }
                ],
            }
        else:
            payload = {
                "name": task.name,
                "board": task.board,
                "requested_iterations": max_iterations,
                "completed_iterations": 1,
                "pass_count": 1,
                "fail_count": 0,
                "ok": True,
                "results": [
                    {"name": task.name, "board": task.board, "iteration": 1, "code": 0, "ok": True, "result": {"ok": True, "plan_schema_kind": "legacy"}}
                ],
            }
        return SimpleNamespace(run=lambda: SimpleNamespace(to_dict=lambda: payload))

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_until_fail(limit=1, path=cfg_path)

    assert code == 2
    assert payload["schema_advisory_summary"] == {
        "structured_step_count": 1,
        "legacy_step_count": 1,
        "test_kind_counts": {"instrument_specific": 1},
        "supported_instrument_status_counts": {"declared_unsupported": 1},
        "warning_messages": ["selected instrument type esp32_meter is not in declared support set"],
        "instrument_specific_steps": ["esp32c6_uart_banner"],
    }


def test_parallel_repeat_until_fail_summary_handles_mixed_supported_and_unsupported(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_spi_banner.json"},
        ],
    }
    cfg_path = _write_setting(tmp_path, setting)

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        status = "declared_supported" if task.name == "esp32c6_spi_banner" else "declared_unsupported"
        warnings = [] if status == "declared_supported" else ["selected instrument type esp32_meter is not in declared support set"]
        payload = {
            "name": task.name,
            "board": task.board,
            "requested_iterations": max_iterations,
            "completed_iterations": 1,
            "pass_count": 1 if status == "declared_supported" else 0,
            "fail_count": 0 if status == "declared_supported" else 1,
            "ok": status == "declared_supported",
            "results": [
                {
                    "name": task.name,
                    "board": task.board,
                    "iteration": 1,
                    "code": 0 if status == "declared_supported" else 2,
                    "ok": status == "declared_supported",
                    "result": {
                        "ok": status == "declared_supported",
                        "plan_schema_kind": "structured",
                        "test_kind": "instrument_specific",
                        "supported_instrument_advisory": {"status": status},
                        "schema_warning_messages": warnings,
                    },
                }
            ],
        }
        return SimpleNamespace(run=lambda: SimpleNamespace(to_dict=lambda: payload))

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_until_fail(limit=1, path=cfg_path)

    assert code == 2
    assert payload["schema_advisory_summary"] == {
        "structured_step_count": 2,
        "legacy_step_count": 0,
        "test_kind_counts": {"instrument_specific": 2},
        "supported_instrument_status_counts": {"declared_supported": 1, "declared_unsupported": 1},
        "warning_messages": ["selected instrument type esp32_meter is not in declared support set"],
        "instrument_specific_steps": ["esp32c6_spi_banner", "esp32c6_uart_banner"],
    }


def test_verify_default_state_surfaces_schema_advisory_summary(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                    {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "results": [
                    {
                        "name": "esp32c6_uart_banner",
                        "ok": True,
                        "result": {
                            "plan_schema_kind": "structured",
                            "test_kind": "instrument_specific",
                            "supported_instrument_advisory": {"status": "declared_supported"},
                            "schema_warning_messages": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    bad = runs_root / "2026-03-19_21-58-00_rp2040_pico_rp2040_gpio_signature"
    bad.mkdir(parents=True)
    (bad / "result.json").write_text(json.dumps({"ok": False, "error_summary": "old failure", "results": []}), encoding="utf-8")

    payload = _verify_default_state(str(setting_path), str(runs_root))

    assert payload["schema_advisory_summary"] == {
        "structured_step_count": 1,
        "legacy_step_count": 1,
        "test_kind_counts": {"instrument_specific": 1},
        "supported_instrument_status_counts": {"declared_supported": 1},
        "warning_messages": [],
        "instrument_specific_steps": ["esp32c6_uart_banner"],
    }
    assert payload["schema_review_status"] == "partial_structured_coverage"
    assert payload["schema_warning_messages"] == []


def test_verify_default_state_prefers_schema_warning_next_action(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    with patch(
        "ael.__main__.inventory_view.describe_test",
        return_value={
            "ok": True,
            "test": {
                "schema_version": "1.0",
                "test_kind": "instrument_specific",
                "supported_instrument_advisory": {
                    "status": "declared_unsupported",
                    "summary": "selected instrument type esp32_meter is not in declared support set",
                },
            },
        },
    ):
        payload = _verify_default_state(str(setting_path), str(runs_root))

    assert payload["health_status"] == "pass"
    assert payload["schema_review_status"] == "warnings_present"
    assert payload["schema_warning_messages"] == ["selected instrument type esp32_meter is not in declared support set"]
    assert payload["next_recommended_action"] == "all steps passing, but review instrument support declarations and schema warnings"


def test_render_verify_default_state_text_includes_schema_summary():
    text = _render_verify_default_state_text(
        {
            "name": "Default Verification",
            "type": "system_baseline",
            "health_status": "pass",
            "configured_steps": 2,
            "current_blocker": "",
            "next_recommended_action": "all steps passing, but review instrument support declarations and schema warnings",
            "last_successful_run": {"step": "esp32c6_devkit/esp32c6_uart_banner", "run_id": "run123"},
            "state_basis": "last_known_run_results",
            "schema_advisory_summary": {
                "structured_step_count": 1,
                "legacy_step_count": 1,
                "test_kind_counts": {"instrument_specific": 1},
                "supported_instrument_status_counts": {"declared_unsupported": 1},
                "warning_messages": ["selected instrument type esp32_meter is not in declared support set"],
                "instrument_specific_steps": ["esp32c6_uart_banner"],
            },
            "validated_tests": [{"step": "esp32c6_devkit/esp32c6_uart_banner", "run_id": "run123"}],
            "failing_tests": [],
        }
    )

    assert "schema_advisory_summary:" in text
    assert "schema_review_status: warnings_present" in text
    assert "schema_review:" in text
    assert "alignment: schema warnings present (1)" in text
    assert "structured_step_count: 1" in text
    assert "legacy_step_count: 1" in text
    assert "test_kind_counts:" in text
    assert "instrument_specific: 1" in text
    assert "supported_instrument_status_counts:" in text
    assert "declared_unsupported: 1" in text
    assert "warning_messages:" in text
    assert "selected instrument type esp32_meter is not in declared support set" in text


def test_render_verify_default_review_text_includes_compact_summary():
    text = _render_verify_default_review_text(
        {
            "health_status": "pass",
            "schema_review_status": "warnings_present",
            "current_blocker": "selected instrument type esp32_meter is not in declared support set",
            "next_recommended_action": "all steps passing, but review instrument support declarations and schema warnings",
            "schema_advisory_summary": {
                "structured_step_count": 1,
                "legacy_step_count": 1,
                "test_kind_counts": {"instrument_specific": 1},
                "supported_instrument_status_counts": {"declared_unsupported": 1},
                "warning_messages": ["selected instrument type esp32_meter is not in declared support set"],
            },
        }
    )

    assert "Default Verification Review" in text
    assert "health_status: pass" in text
    assert "schema_review_status: warnings_present" in text
    assert "structured_coverage: structured=1 legacy=1" in text
    assert "test_kind_distribution: instrument_specific=1" in text
    assert "instrument_support: declared_unsupported=1" in text
    assert "warning_summary: 1 schema warning(s)" in text
    assert "current_blocker: selected instrument type esp32_meter is not in declared support set" in text


def test_verify_default_review_cli_outputs_compact_summary(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "ael",
            "verify-default",
            "review",
            "--file",
            str(setting_path),
            "--runs-root",
            str(runs_root),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert "Default Verification Review" in res.stdout
    assert "schema_review_status: aligned" in res.stdout
    assert "structured_coverage: structured=1 legacy=0" in res.stdout
    assert "warning_summary: none" in res.stdout


def test_status_state_review_surfaces_are_consistent_for_same_baseline(tmp_path):
    setting_path = REPO_ROOT / "configs" / "default_verification_setting.yaml"
    backup = setting_path.read_text(encoding="utf-8") if setting_path.exists() else None
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    try:
        state_res = subprocess.run(
            [
                sys.executable,
                "-m",
                "ael",
                "verify-default",
                "state",
                "--file",
                str(setting_path),
                "--runs-root",
                str(runs_root),
                "--format",
                "json",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        review_res = subprocess.run(
            [
                sys.executable,
                "-m",
                "ael",
                "verify-default",
                "review",
                "--file",
                str(setting_path),
                "--runs-root",
                str(runs_root),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        status_res = subprocess.run(
            [sys.executable, "-m", "ael", "status", "--runs-root", str(runs_root)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
    finally:
        if backup is None:
            setting_path.unlink(missing_ok=True)
        else:
            setting_path.write_text(backup, encoding="utf-8")

    state_payload = json.loads(state_res.stdout)

    assert state_payload["health_status"] == "pass"
    assert state_payload["schema_review_status"] == "aligned"
    assert state_payload["schema_warning_messages"] == []
    assert "schema_review_status: aligned" in review_res.stdout
    assert "warning_summary: none" in review_res.stdout
    assert "default verification:" in status_res.stdout
    assert "[pass]" in status_res.stdout
    assert "schema=aligned" in status_res.stdout


def test_audit_and_verify_default_surfaces_use_consistent_review_vocabulary(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    state = _verify_default_state(str(setting_path), str(runs_root))
    review_text = _render_verify_default_review_text(state)
    audit_report = build_report(REPO_ROOT)

    assert "schema_review_status" in state
    assert "structured_coverage:" in review_text
    assert "warning_summary:" in review_text
    assert "schema_review" in audit_report
    assert "status" in audit_report["schema_review"]
    assert "structured_coverage" in audit_report["schema_review"]
    assert "warning_summary" in audit_report["schema_review"]


def test_ael_status_surfaces_default_verification_schema_review(tmp_path):
    setting_path = REPO_ROOT / "configs" / "default_verification_setting.yaml"
    backup = setting_path.read_text(encoding="utf-8") if setting_path.exists() else None
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    try:
        res = subprocess.run(
            [sys.executable, "-m", "ael", "status", "--runs-root", str(runs_root)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
    finally:
        if backup is None:
            setting_path.unlink(missing_ok=True)
        else:
            setting_path.write_text(backup, encoding="utf-8")

    assert "default verification:" in res.stdout
    assert "readiness=ready" in res.stdout
    assert "schema=aligned" in res.stdout
    assert "coverage=1/0" in res.stdout
    assert "warnings=0" in res.stdout
    assert "next=all steps passing" in res.stdout


def test_verify_default_state_cli_text_renders_schema_summary(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "ael",
            "verify-default",
            "state",
            "--file",
            str(setting_path),
            "--runs-root",
            str(runs_root),
            "--format",
            "text",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert "schema_advisory_summary:" in res.stdout
    assert "baseline_readiness_status: ready" in res.stdout
    assert "schema_review_status: aligned" in res.stdout
    assert "schema_review:" in res.stdout
    assert "structured_step_count: 1" in res.stdout
    assert "supported_instrument_status_counts:" in res.stdout


def test_verify_default_state_cli_json_includes_schema_summary(tmp_path):
    setting_path = tmp_path / "default_verification_setting.json"
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "ael",
            "verify-default",
            "state",
            "--file",
            str(setting_path),
            "--runs-root",
            str(runs_root),
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)

    assert payload["baseline_readiness_status"] == "ready"
    assert payload["schema_review_status"] == "aligned"
    assert "schema_advisory_summary" in payload
    assert payload["schema_advisory_summary"]["structured_step_count"] == 1


def test_sequence_setting_materializes_suite_and_tasks():
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
            {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
        ],
    }

    suite = default_verification._suite_from_setting(setting)

    assert suite.name == "default_verification"
    assert suite.execution_policy["kind"] == "parallel"
    assert [task.name for task in suite.tasks] == ["rp2040_gpio_signature", "stm32f103_gpio_signature"]
    assert [task.board for task in suite.tasks] == ["rp2040_pico", "stm32f103_gpio"]


def test_presets_emit_dut_test_selectors_only():
    rp2040 = default_verification.preset_payload("rp2040_only")
    assert rp2040["board"] == "rp2040_pico"
    assert rp2040["test"] == "tests/plans/rp2040_gpio_signature.json"
    assert "instrument_instance" not in rp2040

    seq = default_verification.preset_payload("esp32s3_then_rp2040")
    assert seq["steps"] == [
        {
            "board": "esp32s3_devkit",
            "test": "tests/plans/esp32s3_gpio_signature_with_meter.json",
        },
        {
            "board": "rp2040_pico",
            "test": "tests/plans/rp2040_gpio_signature.json",
        },
    ]


def test_sequence_setting_rejects_alias_name_and_setup_override():
    setting = {
        "version": 1,
        "mode": "sequence",
        "steps": [
            {
                "name": "stm32_alias",
                "board": "stm32f103_gpio",
                "test": "tests/plans/stm32f103_gpio_signature.json",
                "instrument_instance": "esp32jtag_stm32_golden",
            }
        ],
    }

    ok, error = default_verification._validate_sequence_steps(REPO_ROOT, setting)

    assert ok is False
    assert "must not redefine DUT test identity/setup fields" in error


def test_sequence_setting_rejects_non_dut_test_reference(tmp_path):
    stray = tmp_path / "stray_test.json"
    stray.write_text('{"name":"stray_test"}', encoding="utf-8")
    setting = {
        "version": 1,
        "mode": "sequence",
        "steps": [
            {
                "board": "stm32f103_gpio",
                "test": str(stray),
            }
        ],
    }

    ok, error = default_verification._validate_sequence_steps(REPO_ROOT, setting)

    assert ok is False
    assert "references non-DUT test" in error


def test_sequence_setting_accepts_board_bound_non_inventory_step():
    setting = {
        "version": 1,
        "mode": "sequence",
        "steps": [
            {
                "board": "stm32f103_gpio_stlink",
                "test": "tests/plans/stm32f103_gpio_no_external_capture_stlink.json",
            }
        ],
    }

    ok, error = default_verification._validate_sequence_steps(REPO_ROOT, setting)

    assert ok is True
    assert error == ""


def test_parallel_repeat_until_fail_is_per_worker(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_gpio_signature_with_meter.json"},
        ],
    }
    cfg_path = _write_setting(tmp_path, setting)

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        if task.name == "rp2040_gpio_signature":
            payload = {
                "name": "rp2040_gpio_signature",
                "board": "rp2040_pico",
                "requested_iterations": max_iterations,
                "completed_iterations": 3,
                "pass_count": 2,
                "fail_count": 1,
                "ok": False,
                "results": [
                    {"name": "rp2040_gpio_signature", "board": "rp2040_pico", "iteration": 1, "code": 0, "ok": True, "result": {"ok": True}},
                    {"name": "rp2040_gpio_signature", "board": "rp2040_pico", "iteration": 2, "code": 0, "ok": True, "result": {"ok": True}},
                    {"name": "rp2040_gpio_signature", "board": "rp2040_pico", "iteration": 3, "code": 9, "ok": False, "result": {"error": "rp2040 fail"}},
                ],
            }
        else:
            payload = {
                "name": "esp32c6_gpio_signature_with_meter",
                "board": "esp32c6_devkit",
                "requested_iterations": max_iterations,
                "completed_iterations": 5,
                "pass_count": 5,
                "fail_count": 0,
                "ok": True,
                "results": [
                    {"name": "esp32c6_gpio_signature_with_meter", "board": "esp32c6_devkit", "iteration": i, "code": 0, "ok": True, "result": {"ok": True}}
                    for i in range(1, 6)
                ],
            }
        return SimpleNamespace(run=lambda: SimpleNamespace(to_dict=lambda: payload))

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_until_fail(limit=5, path=cfg_path)

    assert code == 9
    assert payload["requested_iterations_per_worker"] == 5
    by_name = {worker["name"]: worker for worker in payload["workers"]}
    assert by_name["rp2040_gpio_signature"]["completed_iterations"] == 3
    assert by_name["esp32c6_gpio_signature_with_meter"]["completed_iterations"] == 5
    assert payload["failure"]["step_name"] == "rp2040_gpio_signature"
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
    summary = default_verification._task_resource_summary(REPO_ROOT, task)

    assert "dut:esp32c6_devkit" in keys
    assert any(key.endswith("/configs/esp32jtag.yaml") for key in keys)
    assert "instrument:esp32s3_dev_c_meter:192.168.4.1:9000" in keys
    assert summary["dut_ids"] == ["esp32c6_devkit"]
    assert summary["control_instrument_configs"]
    assert summary["instrument_endpoints"] == ["esp32s3_dev_c_meter:192.168.4.1:9000"]


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
    summary = default_verification._task_resource_summary(REPO_ROOT, task)

    assert "dut:esp32c6_devkit" in keys
    assert "instrument:esp32s3_dev_c_meter:192.168.4.1:9000" in keys
    assert not any(key.startswith("probe:") or key.startswith("probe_path:") for key in keys)
    assert summary["control_instrument_endpoints"] == []
    assert summary["control_instrument_configs"] == []
    assert summary["instrument_endpoints"] == ["esp32s3_dev_c_meter:192.168.4.1:9000"]


def test_summarize_resource_keys_groups_known_types():
    summary = summarize_resource_keys(
        [
            "dut:stm32f103",
            "probe:192.168.2.99:4242",
            "probe_path:configs/instrument_instances/esp32jtag_stm32_golden.yaml",
            "serial:/dev/ttyACM1",
            "instrument:esp32s3_dev_c_meter:192.168.4.1:9000",
            "custom:thing",
        ]
    )

    assert summary["dut_ids"] == ["stm32f103"]
    assert summary["control_instrument_endpoints"] == ["192.168.2.99:4242"]
    assert summary["control_instrument_configs"] == ["configs/instrument_instances/esp32jtag_stm32_golden.yaml"]
    assert summary["serial_ports"] == ["/dev/ttyACM1"]
    assert summary["instrument_endpoints"] == ["esp32s3_dev_c_meter:192.168.4.1:9000"]
    assert summary["other"] == ["custom:thing"]


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
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
            {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
        ],
    }

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        def _run():
            if task.name == "rp2040_gpio_signature":
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
    assert by_name["rp2040_gpio_signature"]["fail_count"] == 1
    assert by_name["stm32f103_gpio_signature"]["pass_count"] == 1
    assert len(payload["results"]) == 2
    assert any(item["name"] == "stm32f103_gpio_signature" and item["ok"] for item in payload["results"])


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
    assert "instrument_condition=instrument_api_unavailable" in out
    assert "failure_scope=bench" in out
    assert "policy_class=bench_degraded_retry_once" in out
    assert "error=meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed." in out
    assert "observations=ping=ok,tcp=ok,api=fail" in out


def test_print_worker_totals_includes_verify_failure_details(capsys):
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
                        "error_summary": "instrument digital verification failed",
                        "verify_substage": "instrument.signature",
                        "failure_class": "instrument_digital_mismatch",
                        "observations": {"missing_expected_channels": ["GPIO11"]},
                    }
                }
            ],
        }
    ]

    default_verification._print_worker_totals(lock, workers)
    out = capsys.readouterr().out

    assert "verify_substage=instrument.signature" in out
    assert "failure_class=instrument_digital_mismatch" in out
    assert "instrument_condition=instrument_verify_failed" in out
    assert "failure_scope=verify" in out
    assert "policy_class=verify_no_retry" in out
    assert "error=instrument digital verification failed" in out


def test_parallel_repeat_until_fail_keeps_unrelated_worker_progress_when_instrument_is_bad(tmp_path):
    setting = {
        "version": 1,
        "mode": "sequence",
        "execution_policy": {"kind": "parallel"},
        "steps": [
            {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_gpio_signature_with_meter.json"},
            {"board": "rp2040_pico", "test": "tests/plans/rp2040_gpio_signature.json"},
        ],
    }
    cfg_path = _write_setting(tmp_path, setting)

    def fake_worker(repo_root, task, output_mode, max_iterations, stop_after_failure, log_lock):
        if task.name == "esp32c6_gpio_signature_with_meter":
            payload = {
                "name": task.name,
                "board": task.board,
                "requested_iterations": max_iterations,
                "completed_iterations": 2,
                "pass_count": 1,
                "fail_count": 1,
                "ok": False,
                "results": [
                        {"name": task.name, "board": task.board, "iteration": 1, "code": 0, "ok": True, "result": {"ok": True}},
                    {
                    "name": task.name,
                        "board": task.board,
                        "iteration": 2,
                        "code": 2,
                        "ok": False,
                        "result": {
                            "error": "meter esp32s3_dev_c_meter at 192.168.4.1:9000 accepted tcp but api ping failed.",
                            "failure_class": "network_meter_api",
                            "instrument_condition": "instrument_api_unavailable",
                            "local_instrument_interface_path": "meter_native_api",
                        },
                    },
                ],
            }
        else:
            payload = {
                "name": task.name,
                "board": task.board,
                "requested_iterations": max_iterations,
                "completed_iterations": 5,
                "pass_count": 5,
                "fail_count": 0,
                "ok": True,
                "results": [
                    {"name": task.name, "board": task.board, "iteration": i, "code": 0, "ok": True, "result": {"ok": True}}
                    for i in range(1, 6)
                ],
            }
        return SimpleNamespace(run=lambda: SimpleNamespace(to_dict=lambda: payload))

    with patch("ael.default_verification._worker_for_task", side_effect=fake_worker):
        code, payload = default_verification.run_until_fail(limit=5, path=cfg_path)

    assert code == 2
    by_name = {worker["name"]: worker for worker in payload["workers"]}
    assert by_name["esp32c6_gpio_signature_with_meter"]["completed_iterations"] == 2
    assert by_name["rp2040_gpio_signature"]["completed_iterations"] == 5
    assert payload["failure"]["step_name"] == "esp32c6_gpio_signature_with_meter"
    assert payload["failure"]["failure_scope"] == "bench"
    assert payload["failure"]["instrument_condition"] == "instrument_api_unavailable"
    assert payload["health_summary"]["instrument_condition_counts"] == {"instrument_api_unavailable": 1}
    assert payload["health_summary"]["policy_class_counts"] == {"bench_degraded_retry_once": 1}
    assert payload["health_summary"]["failure_class_counts"] == {"network_meter_api": 1}
    assert payload["health_summary"]["local_instrument_interface_path_counts"] == {"meter_native_api": 1}
    assert payload["health_summary"]["total_pass_count"] == 6
    assert payload["health_summary"]["total_fail_count"] == 1
    assert payload["health_summary"]["worker_pass_counts"]["rp2040_gpio_signature"] == 5
    assert payload["health_summary"]["worker_fail_counts"]["esp32c6_gpio_signature_with_meter"] == 1
    assert payload["health_summary"]["degraded_workers"][0]["name"] == "esp32c6_gpio_signature_with_meter"


def test_run_single_reports_local_instrument_interface_path_for_default_targets(tmp_path):
    rp2040_test = tmp_path / "gpio_signature.json"
    rp2040_test.write_text('{"name":"gpio_signature","pin":"P0.0"}', encoding="utf-8")

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ):
        code, result = default_verification._run_single(
            REPO_ROOT,
            {"board": "rp2040_pico", "test": str(rp2040_test)},
            "normal",
        )

    assert code == 0
    assert result["local_instrument_interface_path"] == "jtag_native_api"
    guard_mock.assert_not_called()

    esp32_test = tmp_path / "esp32c6_gpio_signature_with_meter.json"
    esp32_test.write_text(
        json.dumps(
            {
                "name": "esp32c6_gpio_signature_with_meter",
                "instrument": {"id": "esp32s3_dev_c_meter", "tcp": {"host": "192.168.4.1", "port": 9000}},
                "bench_setup": {"dut_to_instrument": [{"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle"}]},
            }
        ),
        encoding="utf-8",
    )

    with patch("ael.default_verification.instrument_provision.ensure_meter_reachable") as guard_mock, patch(
        "ael.default_verification.run_pipeline",
        return_value=0,
    ):
        code, result = default_verification._run_single(
            tmp_path,
            {"board": "esp32c6_devkit", "test": str(esp32_test)},
            "normal",
        )

    assert code == 0
    assert result["local_instrument_interface_path"] == "meter_native_api"
    guard_mock.assert_called_once()


def test_default_verification_review_payload_normalizes_review_fields():
    payload = default_verification_review_payload(
        {
            "ok": True,
            "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: aligned\nstructured_coverage: structured=3 legacy=0\nwarning_summary: none\n",
        }
    )

    assert payload["ok"] is True
    assert payload["schema_review_status"] == "aligned"
    assert payload["structured_coverage"] == "structured=3 legacy=0"
    assert payload["warning_summary"] == "none"
    assert payload["baseline_readiness_status"] == "ready"
    assert payload["text"].startswith("Default Verification Review")
    assert payload["error"] == ""


def test_default_verification_review_highlights_extracts_status_and_warning_summary():
    review = {
        "ok": True,
        "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: aligned\nstructured_coverage: structured=3 legacy=0\nwarning_summary: none\n",
    }

    highlights = default_verification_review_highlights(review)

    assert highlights == {"health_status": "pass", "schema_review_status": "aligned", "structured_coverage": "structured=3 legacy=0", "warning_summary": "none"}


def test_generate_review_pack_includes_review_highlights_and_body(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(
        "ael_controlplane.review_pack.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: aligned\nstructured_coverage: structured=3 legacy=0\nwarning_summary: none\n",
        },
    )
    monkeypatch.setattr("ael_controlplane.review_pack._run_git", lambda *_args, **_kwargs: "")

    path = generate_review_pack(
        branch="agent/report-review",
        task={
            "title": "report task",
            "task_id": "task_1",
            "execution_mode": "offline",
            "prompt": "review prompt",
            "merge_ready": "no",
            "summary": "review summary",
        },
        artifacts={"run_dir": "runs/report-task"},
    )

    text = path.read_text(encoding="utf-8")
    assert "## Default Verification Review" in text
    assert "- schema_review_status: aligned" in text
    assert "- structured_coverage: structured=3 legacy=0" in text
    assert "- warning_summary: none" in text
    assert "schema_review_status: aligned" in text
    assert "structured_coverage: structured=3 legacy=0" in text
    assert "warning_summary: none" in text
    assert "baseline_readiness_status: ready" in text
    assert "merge_advisory: baseline readiness aligned" in text
    assert "baseline_readiness_status: ready" in text
    assert "merge_advisory: baseline readiness aligned" in text


def test_write_nightly_report_includes_review_highlights_and_body(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ael_controlplane.nightly_report.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: aligned\nstructured_coverage: structured=3 legacy=0\nwarning_summary: none\n",
        },
    )

    path = tmp_path / "reports" / "nightly_2026-03-19.md"
    write_nightly_report(
        "2026-03-19",
        {
            "started_at": "2026-03-19T00:00:00",
            "finished_at": "2026-03-19T00:10:00",
            "ok": True,
            "plans": [],
        },
        path,
    )

    text = path.read_text(encoding="utf-8")
    assert "## Default Verification Review" in text
    assert "- schema_review_status: aligned" in text
    assert "- structured_coverage: structured=3 legacy=0" in text
    assert "- warning_summary: none" in text
    assert "schema_review_status: aligned" in text
    assert "structured_coverage: structured=3 legacy=0" in text
    assert "warning_summary: none" in text
    assert "baseline_readiness_status: ready" in text
    assert "merge_advisory: baseline readiness aligned" in text


def test_review_pack_and_nightly_report_match_review_vocabulary(monkeypatch, tmp_path):
    review_text = (
        "Default Verification Review\n"
        "health_status: pass\n"
        "schema_review_status: warnings_present\n"
        "structured_coverage: structured=3 legacy=1\n"
        "warning_summary: 1 schema warning(s)\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(
        "ael_controlplane.review_pack.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": review_text,
            "schema_review_status": "warnings_present",
            "structured_coverage": "structured=3 legacy=1",
            "warning_summary": "1 schema warning(s)",
        },
    )
    monkeypatch.setattr(
        "ael_controlplane.nightly_report.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": review_text,
            "schema_review_status": "warnings_present",
            "structured_coverage": "structured=3 legacy=1",
            "warning_summary": "1 schema warning(s)",
        },
    )
    monkeypatch.setattr("ael_controlplane.review_pack._run_git", lambda *_args, **_kwargs: "")

    pack_path = generate_review_pack(
        branch="agent/report-review",
        task={
            "title": "report task",
            "task_id": "task_1",
            "execution_mode": "offline",
            "prompt": "review prompt",
            "merge_ready": "no",
            "summary": "review summary",
        },
        artifacts={"run_dir": "runs/report-task"},
    )
    nightly_path = tmp_path / "reports" / "nightly_2026-03-19.md"
    write_nightly_report(
        "2026-03-19",
        {
            "started_at": "2026-03-19T00:00:00",
            "finished_at": "2026-03-19T00:10:00",
            "ok": True,
            "plans": [],
        },
        nightly_path,
    )

    pack_text = pack_path.read_text(encoding="utf-8")
    nightly_text = nightly_path.read_text(encoding="utf-8")
    for expected in (
        "- schema_review_status: warnings_present",
        "baseline_readiness_status: needs_attention",
        "merge_advisory: warning-only: baseline readiness needs attention",
        "- structured_coverage: structured=3 legacy=1",
        "- warning_summary: 1 schema warning(s)",
        "schema_review_status: warnings_present",
        "structured_coverage: structured=3 legacy=1",
        "warning_summary: 1 schema warning(s)",
    ):
        assert expected in pack_text
        assert expected in nightly_text


def test_run_nightly_surfaces_default_verification_review_summary_and_report(monkeypatch, tmp_path):
    review_text = (
        "Default Verification Review\n"
        "health_status: pass\n"
        "schema_review_status: warnings_present\n"
        "structured_coverage: structured=3 legacy=1\n"
        "warning_summary: 1 schema warning(s)\n"
    )
    monkeypatch.setattr("ael_controlplane.nightly.current_branch", lambda: "feature/nightly-test")
    monkeypatch.setattr("ael_controlplane.nightly._collect_backlog", lambda _cfg: [])
    monkeypatch.setattr(
        "ael_controlplane.nightly.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": review_text,
            "schema_review_status": "warnings_present",
            "structured_coverage": "structured=3 legacy=1",
            "warning_summary": "1 schema warning(s)",
        },
    )

    summary = run_nightly(NightlyConfig(dry_run=True, allow_on_master=True, report_root=str(tmp_path / "reports")))

    assert summary["baseline_readiness_status"] == "needs_attention"
    assert summary["schema_review_status"] == "warnings_present"
    assert summary["structured_coverage"] == "structured=3 legacy=1"
    assert summary["warning_summary"] == "1 schema warning(s)"
    assert summary["default_verification_review"]["schema_review_status"] == "warnings_present"
    assert summary["default_verification_review"]["structured_coverage"] == "structured=3 legacy=1"
    assert summary["default_verification_review"]["warning_summary"] == "1 schema warning(s)"
    assert summary["review_pack_paths"] == []

    report_text = Path(summary["report_path"]).read_text(encoding="utf-8")
    assert "## Default Verification Review" in report_text
    assert "- schema_review_status: warnings_present" in report_text
    assert "- structured_coverage: structured=3 legacy=1" in report_text
    assert "- warning_summary: 1 schema warning(s)" in report_text
    assert "structured_coverage: structured=3 legacy=1" in report_text


def test_build_review_pack_payload_exposes_machine_readable_review(monkeypatch):
    monkeypatch.setattr(
        "ael_controlplane.review_pack.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {
            "ok": True,
            "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: aligned\nstructured_coverage: structured=3 legacy=0\nwarning_summary: none\n",
        },
    )
    monkeypatch.setattr("ael_controlplane.review_pack._run_git", lambda *_args, **_kwargs: "")

    payload = build_review_pack_payload(
        branch="agent/report-review",
        task={
            "title": "report task",
            "task_id": "task_1",
            "execution_mode": "offline",
            "prompt": "review prompt",
            "merge_ready": "no",
            "summary": "review summary",
        },
        artifacts={"run_dir": "runs/report-task"},
    )

    assert payload["default_verification_review"]["schema_review_status"] == "aligned"
    assert payload["default_verification_review"]["structured_coverage"] == "structured=3 legacy=0"
    assert payload["default_verification_review"]["warning_summary"] == "none"
    assert payload["baseline_readiness_status"] == "ready"


def test_build_nightly_report_payload_exposes_machine_readable_review():
    payload = build_nightly_report_payload(
        "2026-03-20",
        {
            "started_at": "2026-03-20T00:00:00",
            "finished_at": "2026-03-20T00:10:00",
            "ok": True,
            "plans": [],
            "default_verification_review": {
                "ok": True,
                "text": "Default Verification Review\nhealth_status: pass\nschema_review_status: warnings_present\nstructured_coverage: structured=3 legacy=1\nwarning_summary: 1 schema warning(s)\n",
            },
        },
    )

    assert payload["default_verification_review"]["schema_review_status"] == "warnings_present"
    assert payload["default_verification_review"]["structured_coverage"] == "structured=3 legacy=1"
    assert payload["default_verification_review"]["warning_summary"] == "1 schema warning(s)"
    assert payload["baseline_readiness_status"] == "needs_attention"


def test_review_text_review_pack_payload_nightly_payload_and_summary_stay_consistent(monkeypatch, tmp_path):
    review_text = (
        "Default Verification Review\n"
        "health_status: pass\n"
        "schema_review_status: warnings_present\n"
        "structured_coverage: structured=3 legacy=1\n"
        "warning_summary: 1 schema warning(s)\n"
    )
    expected = {
        "schema_review_status": "warnings_present",
        "structured_coverage": "structured=3 legacy=1",
        "warning_summary": "1 schema warning(s)",
    }
    review_payload = default_verification_review_payload({"ok": True, "text": review_text})

    monkeypatch.setattr(
        "ael_controlplane.review_pack.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {"ok": True, "text": review_text},
    )
    monkeypatch.setattr("ael_controlplane.review_pack._run_git", lambda *_args, **_kwargs: "")
    review_pack_payload = build_review_pack_payload(
        branch="agent/report-review",
        task={
            "title": "report task",
            "task_id": "task_1",
            "execution_mode": "offline",
            "prompt": "review prompt",
            "merge_ready": "no",
            "summary": "review summary",
        },
        artifacts={"run_dir": "runs/report-task"},
    )

    nightly_payload = build_nightly_report_payload(
        "2026-03-20",
        {
            "started_at": "2026-03-20T00:00:00",
            "finished_at": "2026-03-20T00:10:00",
            "ok": True,
            "plans": [],
            "default_verification_review": {"ok": True, "text": review_text},
        },
    )

    monkeypatch.setattr("ael_controlplane.nightly.current_branch", lambda: "feature/nightly-test")
    monkeypatch.setattr("ael_controlplane.nightly._collect_backlog", lambda _cfg: [])
    monkeypatch.setattr(
        "ael_controlplane.nightly.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {"ok": True, "text": review_text},
    )
    summary = run_nightly(NightlyConfig(dry_run=True, allow_on_master=True, report_root=str(tmp_path / "reports")))

    for key, value in expected.items():
        assert review_payload[key] == value
        assert review_pack_payload["default_verification_review"][key] == value
        assert nightly_payload["default_verification_review"][key] == value
        assert summary["default_verification_review"][key] == value


def test_run_nightly_surfaces_top_level_review_keys_and_review_pack_paths(monkeypatch, tmp_path):
    review_text = (
        "Default Verification Review\n"
        "health_status: pass\n"
        "schema_review_status: aligned\n"
        "structured_coverage: structured=4 legacy=0\n"
        "warning_summary: none\n"
    )
    monkeypatch.setattr("ael_controlplane.nightly.current_branch", lambda: "feature/nightly-test")
    monkeypatch.setattr("ael_controlplane.nightly._collect_backlog", lambda _cfg: [])
    monkeypatch.setattr(
        "ael_controlplane.nightly.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {"ok": True, "text": review_text},
    )

    summary = run_nightly(NightlyConfig(dry_run=True, allow_on_master=True, report_root=str(tmp_path / "reports")))

    assert summary["baseline_readiness_status"] == "ready"
    assert summary["schema_review_status"] == "aligned"
    assert summary["structured_coverage"] == "structured=4 legacy=0"
    assert summary["warning_summary"] == "none"
    assert summary["review_pack_paths"] == []


def test_ael_status_surfaces_schema_coverage_and_warning_count(tmp_path):
    setting_path = REPO_ROOT / "configs" / "default_verification_setting.yaml"
    backup = setting_path.read_text(encoding="utf-8") if setting_path.exists() else None
    setting_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "sequence",
                "steps": [
                    {"board": "esp32c6_devkit", "test": "tests/plans/esp32c6_uart_banner.json"},
                    {"board": "stm32f103_gpio", "test": "tests/plans/stm32f103_gpio_signature.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    runs_root = tmp_path / "runs"
    good = runs_root / "2026-03-19_21-57-16_esp32c6_devkit_esp32c6_uart_banner"
    good.mkdir(parents=True)
    (good / "result.json").write_text(json.dumps({"ok": True, "results": []}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    try:
        res = subprocess.run(
            [sys.executable, "-m", "ael", "status", "--runs-root", str(runs_root)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
    finally:
        if backup is None:
            setting_path.unlink(missing_ok=True)
        else:
            setting_path.write_text(backup, encoding="utf-8")

    assert "default verification:" in res.stdout
    assert "readiness=needs_attention" in res.stdout
    assert "schema=partial_structured_coverage" in res.stdout
    assert "coverage=1/1" in res.stdout
    assert "warnings=0" in res.stdout


def test_verify_default_review_text_includes_baseline_readiness_status():
    text = _render_verify_default_review_text(
        {
            "health_status": "pass",
            "schema_review_status": "aligned",
            "schema_advisory_summary": {
                "structured_step_count": 1,
                "legacy_step_count": 0,
                "warning_messages": [],
            },
            "baseline_readiness_status": "ready",
            "current_blocker": "",
            "next_recommended_action": "all steps passing — consider adding next board/test to suite",
        }
    )

    assert "baseline_readiness_status: ready" in text


def test_review_pack_and_nightly_report_surface_baseline_readiness_advisory(monkeypatch, tmp_path):
    review_text = (
        "Default Verification Review\n"
        "health_status: pass\n"
        "schema_review_status: partial_structured_coverage\n"
        "structured_coverage: structured=3 legacy=1\n"
        "warning_summary: none\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(
        "ael_controlplane.review_pack.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {"ok": True, "text": review_text},
    )
    monkeypatch.setattr(
        "ael_controlplane.nightly_report.default_verification_review_snapshot",
        lambda *_args, **_kwargs: {"ok": True, "text": review_text},
    )
    monkeypatch.setattr("ael_controlplane.review_pack._run_git", lambda *_args, **_kwargs: "")

    pack_payload = build_review_pack_payload(
        branch="agent/report-review",
        task={
            "title": "report task",
            "task_id": "task_1",
            "execution_mode": "offline",
            "prompt": "review prompt",
            "merge_ready": "yes",
            "summary": "review summary",
        },
        artifacts={"run_dir": "runs/report-task"},
    )
    nightly_payload = build_nightly_report_payload(
        "2026-03-20",
        {
            "started_at": "2026-03-20T00:00:00",
            "finished_at": "2026-03-20T00:10:00",
            "ok": True,
            "plans": [],
            "baseline_readiness_status": "needs_attention",
            "default_verification_review": {"ok": True, "text": review_text},
        },
    )

    assert pack_payload["baseline_readiness_status"] == "needs_attention"
    assert nightly_payload["baseline_readiness_status"] == "needs_attention"
