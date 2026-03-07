import unittest
from unittest.mock import patch

from ael.adapters import control_download_mode_serial


class TestControlDownloadModeSerial(unittest.TestCase):
    def test_assist_success_returns_role_first_action(self):
        with patch(
            "ael.adapters.control_reset_serial.run",
            return_value={"ok": True, "action_type": "control.download_mode.serial_assist"},
        ) as mocked:
            out = control_download_mode_serial.assist_exit_download_mode({"port": "/dev/ttyFAKE0"})
        mocked.assert_called_once()
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("method"), "rts_reset")
        self.assertEqual(out.get("action_type"), "control.download_mode.serial_assist")
        self.assertEqual(out.get("message"), "RTS reset pulse sent")

    def test_assist_failure_preserves_backend_error(self):
        with patch(
            "ael.adapters.control_reset_serial.run",
            return_value={"ok": False, "error_summary": "control.reset.serial failed on /dev/ttyFAKE0: boom"},
        ):
            out = control_download_mode_serial.assist_exit_download_mode({"port": "/dev/ttyFAKE0"})
        self.assertFalse(out.get("ok"))
        self.assertIn("failed on /dev/ttyFAKE0", out.get("message", ""))


if __name__ == "__main__":
    unittest.main()
