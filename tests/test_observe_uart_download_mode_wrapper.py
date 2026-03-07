import unittest
from unittest.mock import patch

from ael.adapters import observe_uart_log


class TestObserveUartDownloadModeWrapper(unittest.TestCase):
    def test_wrapper_delegates_to_role_first_control(self):
        with patch(
            "ael.adapters.control_download_mode_serial.assist_exit_download_mode",
            return_value={"ok": True, "message": "RTS reset pulse sent"},
        ) as mocked:
            ok, msg = observe_uart_log._try_esp32_rts_reset(serial_mod=object(), port="/dev/ttyFAKE0")
        mocked.assert_called_once()
        self.assertTrue(ok)
        self.assertEqual(msg, "RTS reset pulse sent")


if __name__ == "__main__":
    unittest.main()
