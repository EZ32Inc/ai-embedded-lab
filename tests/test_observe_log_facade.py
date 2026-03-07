import unittest
from unittest.mock import patch

from ael.adapters import observe_log


class TestObserveLogFacade(unittest.TestCase):
    def test_run_serial_log_delegates_to_uart_backend(self):
        cfg = {"enabled": True, "port": "/dev/ttyFAKE0"}
        expected = {"ok": True, "bytes": 1}
        with patch("ael.adapters.observe_uart_log.run", return_value=expected) as mocked:
            result = observe_log.run_serial_log(cfg, raw_log_path="/tmp/fake.log")
        mocked.assert_called_once_with(cfg, raw_log_path="/tmp/fake.log")
        self.assertEqual(result, expected)

    def test_run_alias_uses_serial_log(self):
        cfg = {"enabled": True, "port": "/dev/ttyFAKE0"}
        expected = {"ok": True, "bytes": 2}
        with patch("ael.adapters.observe_log.run_serial_log", return_value=expected) as mocked:
            result = observe_log.run(cfg, raw_log_path="/tmp/fake2.log")
        mocked.assert_called_once_with(cfg, raw_log_path="/tmp/fake2.log")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
