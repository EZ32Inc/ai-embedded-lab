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


    def test_run_uses_esp32jtag_web_uart_backend_when_selected(self):
        with TemporaryDirectory() as td:
            raw_log = Path(td) / "uart.log"
            cfg = {
                "enabled": True,
                "port": "s3jtag_internal_web_uart",
                "baud": 115200,
                "duration_s": 1,
                "expect_patterns": ["AEL_READY RP2040 UART"],
                "backend": "esp32jtag_web_uart",
                "bridge_endpoint": "https://192.168.4.1:443",
            }
            with patch(
                "ael.adapters.observe_uart_log._capture_via_esp32jtag_web_uart",
                return_value=(b"AEL_READY RP2040 UART\r\n", None),
            ) as mocked:
                result = observe_uart_log.run(cfg, str(raw_log))

        mocked.assert_called_once_with("https://192.168.4.1:443", 1.0, 0.2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["backend"], "esp32jtag_web_uart")
        self.assertEqual(result["bridge_endpoint"], "https://192.168.4.1:443")


if __name__ == "__main__":
    unittest.main()
