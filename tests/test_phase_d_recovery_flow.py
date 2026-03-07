import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from ael.adapter_registry import AdapterRegistry
from ael import evidence
from ael import runner


class _FakeSerial:
    def __init__(self, *args, **kwargs):
        self.rts = False
        self.dtr = False

    def close(self):
        return None


class TestPhaseDRecoveryFlow(unittest.TestCase):
    def setUp(self):
        self.run_dir = Path("/tmp/ael_phase_d_recovery_flow")
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def tearDown(self):
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_fail_first_recovery_then_pass(self):
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
                        "expected_hz": 10.0,
                        "min_edges": 1,
                        "max_edges": 100,
                        "log_path": "",
                        "measure_path": str(self.run_dir / "measure.json"),
                        "test_limits": {},
                        "recovery_demo": {
                            "fail_first": True,
                            "action_type": "reset.serial",
                            "params": {"port": "/dev/ttyFAKE0", "baud": 115200, "pulse_ms": 50, "settle_ms": 50},
                        },
                    },
                }
            ],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 2}},
        }
        def _fake_observe(_probe_cfg, pin, duration_s, expected_hz, min_edges, max_edges, capture_out, verify_edges):
            capture_out["blob"] = b"\x00\xff" * 64
            capture_out["sample_rate_hz"] = 1000
            capture_out["bit"] = 0
            return True

        with patch("ael.adapter_registry.observe_gpio_pin.run", side_effect=_fake_observe), patch(
            "ael.adapter_registry.la_verify.analyze_capture_bytes",
            return_value={"ok": True, "metrics": {"freq_hz": 10.0, "duty": 0.5}, "reasons": []},
        ), patch("ael.adapter_registry.time.sleep", return_value=None), patch("serial.Serial", _FakeSerial):
            res = runner.run_plan(plan, self.run_dir, registry)

        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("termination"), "pass")
        self.assertEqual(len(res.get("recovery", [])), 1)
        self.assertEqual(res["recovery"][0].get("action_type"), "reset.serial")
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertEqual(res["recovery"][0].get("failure_kind"), "verification_miss")
        self.assertIsInstance(res["recovery"][0].get("recovery_hint"), dict)
        self.assertEqual(res["recovery"][0]["recovery_hint"].get("preferred_action"), "reset.serial")

        step_entries = [s for s in res.get("steps", []) if s.get("name") == "check_signal"]
        self.assertEqual(len(step_entries), 2)
        self.assertFalse(step_entries[0].get("ok"))
        self.assertTrue(step_entries[1].get("ok"))

        ev_path = evidence.write_runner_evidence(self.run_dir, res)
        payload = Path(ev_path).read_text(encoding="utf-8")
        self.assertIn("recovery.action", payload)
        self.assertIn("gpio.signal", payload)


if __name__ == "__main__":
    unittest.main()
