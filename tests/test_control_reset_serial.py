import unittest
from unittest.mock import patch

from ael.adapters import control_reset_serial


class _FakeSerial:
    def __init__(self, *args, **kwargs):
        self.rts = False
        self.dtr = True

    def close(self):
        return None


class TestControlResetSerial(unittest.TestCase):
    def test_requires_port(self):
        out = control_reset_serial.run({}, action_type="control.reset.serial")
        self.assertFalse(out.get("ok"))
        self.assertIn("requires params.port", out.get("error_summary", ""))

    def test_success_returns_action_details(self):
        with patch("serial.Serial", _FakeSerial), patch("ael.adapters.control_reset_serial.time.sleep", return_value=None):
            out = control_reset_serial.run(
                {"port": "/dev/ttyFAKE0", "baud": 9600, "pulse_ms": 25, "settle_ms": 80},
                action_type="control.reset.serial",
            )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("action_type"), "control.reset.serial")
        self.assertEqual(out.get("port"), "/dev/ttyFAKE0")
        self.assertEqual(out.get("baud"), 9600)


if __name__ == "__main__":
    unittest.main()
