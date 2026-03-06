import unittest
from unittest.mock import patch

from ael.adapters import preflight


class TestPreflightBehavior(unittest.TestCase):
    def test_monitor_and_la_can_override_transient_ping_tcp_failures(self):
        probe_cfg = {"ip": "192.168.2.63", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"}
        with patch("ael.adapters.preflight._ping", return_value=False), patch(
            "ael.adapters.preflight._check_tcp", return_value=False
        ), patch(
            "ael.adapters.preflight._monitor_targets", return_value=(True, ["M0+", "Rescue (Attach to reset)"])
        ), patch(
            "ael.adapters.preflight._la_self_test", return_value=True
        ), patch(
            "ael.adapters.preflight._fetch_port_config", return_value={}
        ):
            ok, info = preflight.run(probe_cfg)
        self.assertTrue(ok)
        self.assertFalse(info.get("ping_ok"))
        self.assertFalse(info.get("tcp_ok"))
        self.assertTrue(info.get("monitor_ok"))
        self.assertTrue(info.get("la_ok"))

    def test_monitor_failure_still_fails_preflight(self):
        probe_cfg = {"ip": "192.168.2.63", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"}
        with patch("ael.adapters.preflight._ping", return_value=True), patch(
            "ael.adapters.preflight._check_tcp", return_value=True
        ), patch(
            "ael.adapters.preflight._monitor_targets", return_value=(False, [])
        ), patch(
            "ael.adapters.preflight._la_self_test", return_value=True
        ), patch(
            "ael.adapters.preflight._fetch_port_config", return_value={}
        ):
            ok, info = preflight.run(probe_cfg)
        self.assertFalse(ok)
        self.assertFalse(info.get("monitor_ok"))


if __name__ == "__main__":
    unittest.main()
