import unittest
from unittest.mock import patch

from ael import la_check


class TestLaCheck(unittest.TestCase):
    def test_run_reports_toggling_when_edges_present(self):
        def _fake_observe(probe_cfg, pin, duration_s, expected_hz, min_edges, max_edges, capture_out=None, verify_edges=True):
            if capture_out is not None:
                capture_out.update({"edges": 8, "high": 300, "low": 320, "sample_rate_hz": 260000, "window_s": 0.25})
            return True

        with patch("ael.la_check.resolve_probe_cfg", return_value=("configs/esp32jtag.yaml", {"name": "ESP32JTAG", "ip": "192.168.2.98"})), patch(
            "ael.la_check.observe_gpio_pin.run",
            side_effect=_fake_observe,
        ):
            out = la_check.run(pin="P0.0", board="stm32f103", duration_s=1.0, min_edges=1)

        self.assertTrue(out["ok"])
        self.assertTrue(out["toggling"])
        self.assertEqual(8, out["edges"])
        self.assertEqual("configs/esp32jtag.yaml", out["control_instrument_config"])
        self.assertEqual("ESP32JTAG", out["control_instrument_name"])
        self.assertEqual("192.168.2.98", out["control_instrument_host"])
        self.assertEqual("configs/esp32jtag.yaml", out["control_instrument"]["config"])

    def test_run_reports_not_toggling_when_zero_edges(self):
        def _fake_observe(probe_cfg, pin, duration_s, expected_hz, min_edges, max_edges, capture_out=None, verify_edges=True):
            if capture_out is not None:
                capture_out.update({"edges": 0, "high": 65532, "low": 0, "sample_rate_hz": 260000, "window_s": 0.252})
            return True

        with patch("ael.la_check.resolve_probe_cfg", return_value=("configs/esp32jtag.yaml", {"name": "ESP32JTAG", "ip": "192.168.2.98"})), patch(
            "ael.la_check.observe_gpio_pin.run",
            side_effect=_fake_observe,
        ):
            out = la_check.run(pin="P0.0", board="stm32f103", duration_s=1.0, min_edges=1)

        self.assertTrue(out["ok"])
        self.assertFalse(out["toggling"])
        self.assertEqual(0, out["edges"])
        self.assertEqual("ESP32JTAG", out["control_instrument"]["name"])


if __name__ == "__main__":
    unittest.main()
