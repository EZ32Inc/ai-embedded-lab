from unittest.mock import patch

from ael import default_verification


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
