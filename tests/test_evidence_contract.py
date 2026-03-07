import json
import shutil
import unittest
from pathlib import Path

from ael import evidence


class TestEvidenceContract(unittest.TestCase):
    def setUp(self):
        self.run_dir = Path("/tmp/ael_evidence_contract_test")
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def tearDown(self):
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_make_item_shape(self):
        item = evidence.make_item(
            kind="gpio.signal",
            source="check.signal_verify",
            ok=True,
            summary="ok",
            facts={"freq_hz": 1000},
            artifacts={"measure_json": "/tmp/measure.json"},
        )
        self.assertEqual(item["status"], "pass")
        self.assertEqual(item["kind"], "gpio.signal")
        self.assertEqual(item["source"], "check.signal_verify")
        self.assertIsInstance(item["facts"], dict)
        self.assertIsInstance(item["artifacts"], dict)

    def test_collect_and_write_runner_evidence(self):
        runner_result = {
            "steps": [
                {
                    "name": "check_signal",
                    "type": "check.signal_verify",
                    "ok": True,
                    "result": {
                        "ok": True,
                        "evidence": [
                            evidence.make_item(
                                kind="gpio.signal",
                                source="check.signal_verify",
                                ok=True,
                                summary="signal verify passed",
                                facts={"pin": "PA0"},
                                artifacts={"measure_json": "/tmp/measure.json"},
                            )
                        ],
                    },
                }
            ]
        }
        out_path = evidence.write_runner_evidence(self.run_dir, runner_result)
        payload = json.loads(Path(out_path).read_text(encoding="utf-8"))
        self.assertEqual(payload.get("version"), evidence.EVIDENCE_VERSION)
        self.assertIsInstance(payload.get("items"), list)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["kind"], "gpio.signal")
        self.assertEqual(payload["items"][0]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
