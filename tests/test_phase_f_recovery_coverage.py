import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from ael.adapter_registry import AdapterRegistry
from ael import runner


class _FakeSerial:
    def __init__(self, *args, **kwargs):
        self.rts = False
        self.dtr = False

    def close(self):
        return None


class TestPhaseFRecoveryCoverage(unittest.TestCase):
    def setUp(self):
        self.run_dir = Path("/tmp/ael_phase_f_recovery")
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def tearDown(self):
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_uart_recovery_to_success(self):
        registry = AdapterRegistry()
        plan = {
            "steps": [
                {
                    "name": "check_uart",
                    "type": "check.uart_log",
                    "retry_budget": 0,
                    "rewind_anchor": "check_uart",
                    "inputs": {
                        "observe_uart_cfg": {
                            "enabled": True,
                            "port": "/dev/ttyFAKE0",
                            "baud": 115200,
                            "recovery_demo": {
                                "fail_first": True,
                                "action_type": "reset.serial",
                                "params": {"port": "/dev/ttyFAKE0", "baud": 115200},
                            },
                        },
                        "raw_log_path": str(self.run_dir / "uart.log"),
                        "out_json": str(self.run_dir / "uart.json"),
                        "flash_json_path": "",
                        "output_mode": "normal",
                        "log_path": "",
                    },
                }
            ],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 2}},
        }

        with patch(
            "ael.adapter_registry.observe_log.run_serial_log",
            return_value={"ok": True, "bytes": 22, "lines": 2, "error_summary": ""},
        ), patch("ael.adapter_registry.time.sleep", return_value=None), patch("serial.Serial", _FakeSerial):
            res = runner.run_plan(plan, self.run_dir, registry)

        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("termination"), "pass")
        self.assertEqual(len(res.get("recovery", [])), 1)
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertEqual(res["recovery"][0].get("action_type"), "reset.serial")
        step_entries = [s for s in res.get("steps", []) if s.get("name") == "check_uart"]
        self.assertEqual(len(step_entries), 2)
        self.assertFalse(step_entries[0].get("ok"))
        self.assertTrue(step_entries[1].get("ok"))

    def test_signal_recovery_attempted_but_still_fail(self):
        registry = AdapterRegistry()
        plan = {
            "steps": [
                {
                    "name": "check_signal",
                    "type": "check.signal_verify",
                    "retry_budget": 0,
                    "rewind_anchor": "check_signal",
                    "inputs": {
                        "probe_cfg": {},
                        "pin": "PA0",
                        "duration_s": 0.1,
                        "expected_hz": 1.0,
                        "min_edges": 1,
                        "max_edges": 10,
                        "log_path": "",
                        "measure_path": str(self.run_dir / "measure.json"),
                        "test_limits": {},
                        "recovery_demo": {
                            "fail_first": True,
                            "fail_after_recovery": True,
                            "action_type": "reset.serial",
                            "params": {"port": "/dev/ttyFAKE0", "baud": 115200},
                        },
                    },
                }
            ],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 2}},
        }
        with patch("ael.adapter_registry.time.sleep", return_value=None), patch("serial.Serial", _FakeSerial):
            res = runner.run_plan(plan, self.run_dir, registry)

        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("termination"), "fail")
        self.assertEqual(res.get("failure_kind"), "non_recoverable")
        self.assertEqual(len(res.get("recovery", [])), 1)
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertEqual(res["recovery"][0].get("action_type"), "reset.serial")
        step_entries = [s for s in res.get("steps", []) if s.get("name") == "check_signal"]
        self.assertEqual(len(step_entries), 2)
        self.assertFalse(step_entries[0].get("ok"))
        self.assertFalse(step_entries[1].get("ok"))


if __name__ == "__main__":
    unittest.main()
