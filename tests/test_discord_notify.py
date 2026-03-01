import unittest

from notifiers import discord_webhook


class TestDiscordNotifyFormat(unittest.TestCase):
    def test_format_message_includes_core_fields(self):
        event = {
            "type": "run_failed",
            "severity": "error",
            "run_id": "2026-03-01_test",
            "dut": "esp32s3_devkit",
            "step": "flash",
            "summary": "flash failed",
            "details": "timeout",
            "artifacts_path": "runs/test",
        }
        cfg = {"mention": "@here"}
        log_tails = {"flash": ["line1", "line2"]}
        msg = discord_webhook._format_message(event, cfg, log_tails)
        self.assertIn("@here", msg)
        self.assertIn("esp32s3_devkit", msg)
        self.assertIn("flash failed", msg)
        self.assertIn("line1", msg)


if __name__ == "__main__":
    unittest.main()
