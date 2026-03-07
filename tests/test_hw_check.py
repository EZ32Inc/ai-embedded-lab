import unittest
from unittest.mock import patch

from ael import hw_check


class TestHwCheck(unittest.TestCase):
    def test_run_success_without_expect_pattern(self):
        with patch("ael.hw_check.load_board_target", return_value=("configs/boards/esp32c3_devkit.yaml", "esp32c3")), patch(
            "ael.hw_check.port_stability_check",
            return_value={"port": "/dev/ttyACM0", "samples": 3, "present_count": 3, "stable": True, "observed": [True, True, True]},
        ), patch(
            "ael.hw_check.probe_chip",
            return_value={"ok": True, "chip_line": "Chip is ESP32-C3", "mac": "50:78:7d:e2:24:50", "raw": "ok"},
        ), patch(
            "ael.hw_check.capture_boot_log",
            return_value={
                "ok": True,
                "reset_ok": True,
                "serial_nonempty": True,
                "serial_sample": "I/main hello",
                "serial_text": "I/main hello",
                "reset_raw": "ok",
            },
        ):
            out = hw_check.run(board="esp32c3_devkit", port="/dev/ttyACM0", samples=3, interval_s=0)
        self.assertTrue(out["ok"])
        self.assertEqual("esp32c3", out["target"])

    def test_run_fails_when_expect_pattern_missing(self):
        with patch("ael.hw_check.load_board_target", return_value=("configs/boards/esp32c3_devkit.yaml", "esp32c3")), patch(
            "ael.hw_check.port_stability_check",
            return_value={"port": "/dev/ttyACM0", "samples": 2, "present_count": 2, "stable": True, "observed": [True, True]},
        ), patch(
            "ael.hw_check.probe_chip",
            return_value={"ok": True, "chip_line": "Chip is ESP32-C3", "mac": "50:78:7d:e2:24:50", "raw": "ok"},
        ), patch(
            "ael.hw_check.capture_boot_log",
            return_value={
                "ok": True,
                "reset_ok": True,
                "serial_nonempty": True,
                "serial_sample": "I/main hello",
                "serial_text": "I/main hello",
                "reset_raw": "ok",
            },
        ):
            out = hw_check.run(board="esp32c3_devkit", port="/dev/ttyACM0", expect_pattern="AEL_DUT_READY", samples=2, interval_s=0)
        self.assertFalse(out["ok"])
        self.assertFalse(out["expect_ok"])

    def test_run_passes_when_expect_pattern_in_full_uart_text(self):
        with patch("ael.hw_check.load_board_target", return_value=("configs/boards/esp32c3_devkit.yaml", "esp32c3")), patch(
            "ael.hw_check.port_stability_check",
            return_value={"port": "/dev/ttyACM0", "samples": 2, "present_count": 2, "stable": True, "observed": [True, True]},
        ), patch(
            "ael.hw_check.probe_chip",
            return_value={"ok": True, "chip_line": "Chip is ESP32-C3", "mac": "50:78:7d:e2:24:50", "raw": "ok"},
        ), patch(
            "ael.hw_check.capture_boot_log",
            return_value={
                "ok": True,
                "reset_ok": True,
                "serial_nonempty": True,
                "serial_sample": "I/main hello",
                "serial_text": "I/main hello\nAEL_DUT_READY\n",
                "reset_raw": "ok",
            },
        ):
            out = hw_check.run(board="esp32c3_devkit", port="/dev/ttyACM0", expect_pattern="AEL_DUT_READY", samples=2, interval_s=0)
        self.assertTrue(out["ok"])
        self.assertTrue(out["expect_ok"])


if __name__ == "__main__":
    unittest.main()
