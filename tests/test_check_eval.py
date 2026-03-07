import unittest

from ael import check_eval


class TestCheckEval(unittest.TestCase):
    def test_signal_eval_paths(self):
        v = check_eval.evaluate_signal_facts({"observe_ok": False})
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "transport_error")

        v = check_eval.evaluate_signal_facts({"observe_ok": True, "has_capture": False})
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "verification_miss")

        v = check_eval.evaluate_signal_facts({"observe_ok": True, "has_capture": True, "measure_ok": False})
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "verification_mismatch")

        v = check_eval.evaluate_signal_facts({"observe_ok": True, "has_capture": True, "measure_ok": True})
        self.assertTrue(v["ok"])

    def test_uart_eval_download_mode_hint(self):
        v = check_eval.evaluate_uart_facts(
            {"ok": False, "download_mode_detected": True, "error_summary": "failed"},
            {"port": "/dev/ttyACM0", "baud": 115200},
        )
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "verification_miss")
        self.assertIsInstance(v["recovery_hint"], dict)
        self.assertEqual(v["recovery_hint"]["preferred_action"], "reset.serial")

    def test_instrument_signature_eval(self):
        v = check_eval.evaluate_instrument_signature_facts({"backend_ready": False, "error_summary": "not ready"})
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "instrument_not_ready")

        v = check_eval.evaluate_instrument_signature_facts({"backend_ready": True, "mismatch_count": 1})
        self.assertFalse(v["ok"])
        self.assertEqual(v["failure_kind"], "verification_mismatch")

        v = check_eval.evaluate_instrument_signature_facts({"backend_ready": True, "mismatch_count": 0})
        self.assertTrue(v["ok"])


if __name__ == "__main__":
    unittest.main()
