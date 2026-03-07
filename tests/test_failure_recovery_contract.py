import unittest

from ael import failure_recovery


class TestFailureRecoveryContract(unittest.TestCase):
    def test_make_and_normalize_recovery_hint(self):
        hint = failure_recovery.make_recovery_hint(
            kind="verification_miss",
            recoverable=True,
            preferred_action="reset.serial",
            reason="demo",
            scope="step",
            retry=True,
            params={"port": "/dev/ttyACM0"},
        )
        self.assertEqual(hint.get("kind"), "verification_miss")
        self.assertEqual(hint.get("preferred_action"), "reset.serial")
        self.assertEqual(hint.get("action_type"), "reset.serial")

        norm = failure_recovery.normalize_recovery_hint(hint)
        self.assertIsInstance(norm, dict)
        self.assertEqual(norm.get("kind"), "verification_miss")
        self.assertEqual(norm.get("preferred_action"), "reset.serial")

    def test_normalize_failure_kind(self):
        self.assertEqual(failure_recovery.normalize_failure_kind("timeout"), "timeout")
        self.assertEqual(failure_recovery.normalize_failure_kind("NOPE"), "unknown")

    def test_recovery_action_aliases_for_serial_reset(self):
        legacy = failure_recovery.recovery_action_aliases("reset.serial")
        role_first = failure_recovery.recovery_action_aliases("control.reset.serial")
        self.assertIn("reset.serial", legacy)
        self.assertIn("control.reset.serial", legacy)
        self.assertIn("reset.serial", role_first)
        self.assertIn("control.reset.serial", role_first)


if __name__ == "__main__":
    unittest.main()
