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


if __name__ == "__main__":
    unittest.main()
