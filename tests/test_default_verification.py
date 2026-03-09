from pathlib import Path
from unittest.mock import patch

from ael import default_verification


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    assert run_mock.call_args.kwargs["probe_path"].endswith("configs/esp32jtag_rp2040.yaml")


def test_run_until_fail_stops_on_first_failure():
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
        code, payload = default_verification.run_until_fail(limit=10)

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


def test_run_until_fail_reports_success_when_all_runs_pass():
    with patch(
        "ael.default_verification.run_default_setting",
        side_effect=[
            (0, {"ok": True, "mode": "sequence", "results": []}),
            (0, {"ok": True, "mode": "sequence", "results": []}),
            (0, {"ok": True, "mode": "sequence", "results": []}),
        ],
    ):
        code, payload = default_verification.run_until_fail(limit=3)

    assert code == 0
    assert payload["ok"] is True
    assert payload["completed_runs"] == 3
    assert len(payload["runs"]) == 3
