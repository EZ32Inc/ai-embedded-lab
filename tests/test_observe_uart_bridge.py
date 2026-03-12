import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from ael.adapters import observe_uart_log


class TestObserveUartBridge(unittest.TestCase):
    def test_run_uses_bridge_endpoint_when_present(self):
        with TemporaryDirectory() as td:
            raw_log = Path(td) / "uart.log"
            cfg = {
                "enabled": True,
                "port": "/dev/ttyUSB0",
                "baud": 115200,
                "duration_s": 1,
                "expect_patterns": ["AEL_READY STM32F103 UART"],
                "bridge_endpoint": "127.0.0.1:8767",
            }
            with patch(
                "ael.adapters.observe_uart_log._capture_via_bridge",
                return_value=(b"AEL_READY STM32F103 UART\r\n", None),
            ) as mocked:
                result = observe_uart_log.run(cfg, str(raw_log))

        mocked.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["bridge_endpoint"], "127.0.0.1:8767")
        self.assertEqual(result["port"], "/dev/ttyUSB0")
        self.assertEqual(result["missing_expect"], [])


if __name__ == "__main__":
    unittest.main()
