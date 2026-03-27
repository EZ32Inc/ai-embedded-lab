import unittest
from unittest.mock import Mock, patch

from ael.adapters import observe_gpio_pin


class TestObserveGpioPin(unittest.TestCase):
    def test_run_uses_uart_rxd_detect_for_uart_rx_pin(self):
        post_response = Mock()
        post_response.raise_for_status.return_value = None

        status_response = Mock()
        status_response.raise_for_status.return_value = None
        status_response.content = b'{"state":"completed"}'
        status_response.json.return_value = {"state": "completed"}

        result_payload = {
            "test": "test_uart_rxd_detect",
            "result": "pass",
            "state": "toggle",
            "samples": 1000,
            "high": 990,
            "low": 10,
            "transitions": 20,
            "estimated_hz": 10,
        }
        result_response = Mock()
        result_response.raise_for_status.return_value = None
        result_response.content = b'1'
        result_response.json.return_value = result_payload

        capture = {}
        probe_cfg = {
            "ip": "192.168.4.1",
            "web_scheme": "https",
            "web_port": 443,
            "web_user": "admin",
            "web_pass": "admin",
            "web_verify_ssl": False,
            "web_suppress_ssl_warnings": True,
        }

        with patch("ael.adapters.observe_gpio_pin.requests.post", return_value=post_response) as mock_post, \
             patch("ael.adapters.observe_gpio_pin.requests.get", side_effect=[status_response, result_response]) as mock_get:
            ok = observe_gpio_pin.run(
                probe_cfg,
                pin="UART_RXD",
                duration_s=1.0,
                expected_hz=1.0,
                min_edges=1,
                max_edges=200,
                capture_out=capture,
                verify_edges=False,
                expected_state="toggle",
            )

        self.assertTrue(ok)
        self.assertEqual({"test_type": "test_uart_rxd_detect"}, mock_post.call_args.kwargs["json"])
        self.assertEqual(2, mock_get.call_count)
        self.assertEqual(result_payload, capture["uart_rxd_result"])
        self.assertEqual(b"UART_RXD", capture["blob"])
        self.assertEqual(20, capture["edges"])


if __name__ == "__main__":
    unittest.main()
