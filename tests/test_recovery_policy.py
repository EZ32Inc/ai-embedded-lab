import unittest

from ael import recovery_policy


class TestRecoveryPolicy(unittest.TestCase):
    def test_resolve_hint_keeps_existing_recoverable_hint(self):
        step = {"type": "check.noop"}
        out = {
            "failure_kind": "verification_miss",
            "recovery_hint": {
                "kind": "verification_miss",
                "recoverable": True,
                "preferred_action": "reset.serial",
                "action_type": "reset.serial",
                "reason": "test",
                "params": {"port": "/dev/ttyFAKE0"},
            },
        }
        hint = recovery_policy.resolve_hint(step, out)
        self.assertIsInstance(hint, dict)
        self.assertEqual(hint.get("action_type"), "reset.serial")

    def test_resolve_hint_synthesizes_uart_default(self):
        step = {
            "type": "check.uart_log",
            "inputs": {"observe_uart_cfg": {"port": "/dev/ttyFAKE0", "baud": 115200}},
        }
        out = {"failure_kind": "verification_miss", "error_summary": "expected UART patterns missing"}
        hint = recovery_policy.resolve_hint(step, out)
        self.assertIsInstance(hint, dict)
        self.assertEqual(hint.get("action_type"), "reset.serial")
        self.assertEqual(hint.get("params", {}).get("port"), "/dev/ttyFAKE0")

    def test_action_attempt_limit_for_serial_reset(self):
        attempts = {"reset.serial": 1}
        self.assertFalse(recovery_policy.allow_action_attempt("reset.serial", attempts))
        self.assertFalse(recovery_policy.allow_action_attempt("control.reset.serial", attempts))


if __name__ == "__main__":
    unittest.main()
