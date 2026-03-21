import socket
import unittest
from unittest.mock import MagicMock, patch

from ael.adapters import preflight
from ael.adapters.preflight import PreflightIssue, check_connection_readiness, _tcp_ping


class TestTcpPing(unittest.TestCase):
    def test_missing_endpoint_returns_false(self):
        self.assertFalse(_tcp_ping(""))
        self.assertFalse(_tcp_ping(None))

    def test_no_colon_returns_false(self):
        self.assertFalse(_tcp_ping("192.168.1.1"))

    def test_reachable_endpoint_returns_true(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=None)
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch("socket.create_connection", return_value=mock_conn):
            self.assertTrue(_tcp_ping("192.168.1.1:4242"))

    def test_unreachable_endpoint_returns_false(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertFalse(_tcp_ping("192.168.1.1:4242"))


class TestCheckConnectionReadiness(unittest.TestCase):
    def test_non_dict_bench_setup_returns_empty(self):
        issues = check_connection_readiness(None)
        self.assertEqual(issues, [])
        issues = check_connection_readiness("not_a_dict")
        self.assertEqual(issues, [])

    def test_no_issues_when_all_provisioned(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "power", "instrument_id": "ps1", "status": "provisioned", "required": True},
            ]
        }
        issues = check_connection_readiness(bench_setup)
        blocking = [i for i in issues if i.severity == "blocking"]
        self.assertEqual(blocking, [])

    def test_blocking_issue_for_defined_not_provisioned(self):
        bench_setup = {
            "external_inputs": [
                {"dut_signal": "SIG_IN", "kind": "clock", "status": "defined_not_provisioned", "required": True},
            ]
        }
        issues = check_connection_readiness(bench_setup)
        blocking = [i for i in issues if i.severity == "blocking"]
        self.assertEqual(len(blocking), 1)
        self.assertEqual(blocking[0].kind, "connection_setup_incomplete")

    def test_instrument_role_unreachable_is_blocking(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "scope", "instrument_id": "osc1", "status": "provisioned",
                 "required": True, "endpoint": "192.168.1.100:5025"},
            ]
        }
        with patch("ael.adapters.preflight._tcp_ping", return_value=False):
            issues = check_connection_readiness(bench_setup)
        blocking = [i for i in issues if i.severity == "blocking"]
        self.assertTrue(any(i.kind == "instrument_role_unreachable" for i in blocking))

    def test_instrument_role_reachable_no_issue(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "scope", "instrument_id": "osc1", "status": "provisioned",
                 "required": True, "endpoint": "192.168.1.100:5025"},
            ]
        }
        with patch("ael.adapters.preflight._tcp_ping", return_value=True):
            issues = check_connection_readiness(bench_setup)
        self.assertFalse(any(i.kind == "instrument_role_unreachable" for i in issues))

    def test_optional_role_unreachable_is_not_checked(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "aux", "instrument_id": "aux1", "status": "provisioned",
                 "required": False, "endpoint": "192.168.1.200:9999"},
            ]
        }
        with patch("ael.adapters.preflight._tcp_ping", return_value=False):
            issues = check_connection_readiness(bench_setup)
        self.assertFalse(any(i.kind == "instrument_role_unreachable" for i in issues))

    def test_wiring_not_verified_is_advisory(self):
        bench_setup = {
            "dut_to_instrument": [
                {"dut_gpio": "PA4", "inst_gpio": "0"},
            ]
        }
        issues = check_connection_readiness(bench_setup)
        advisory = [i for i in issues if i.severity == "advisory"]
        self.assertTrue(any(i.kind == "wiring_not_verified" for i in advisory))

    def test_wiring_with_discovery_status_no_advisory(self):
        bench_setup = {
            "dut_to_instrument": [
                {"dut_gpio": "PA4", "inst_gpio": "0"},
            ],
            "discovery_status": "verified",
        }
        issues = check_connection_readiness(bench_setup)
        self.assertFalse(any(i.kind == "wiring_not_verified" for i in issues))

    def test_preflight_issue_fields(self):
        issue = PreflightIssue(kind="test_kind", severity="blocking", message="test message")
        self.assertEqual(issue.kind, "test_kind")
        self.assertEqual(issue.severity, "blocking")
        self.assertEqual(issue.message, "test message")


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

    def test_classify_monitor_failure_marks_probe_busy(self):
        kind = preflight._classify_monitor_failure('Command timed out after 8 seconds', True)
        self.assertEqual(kind, "probe_busy_or_stuck")

    def test_classify_monitor_failure_marks_transport_unhealthy(self):
        kind = preflight._classify_monitor_failure('connection refused', False)
        self.assertEqual(kind, "probe_transport_unhealthy")


if __name__ == "__main__":
    unittest.main()
