import shutil
import unittest
from pathlib import Path

from ael import runner


class _FlakyAdapter:
    def __init__(self, fail_attempts: int):
        self._fail_attempts = int(fail_attempts)
        self.calls = 0

    def execute(self, step, plan, ctx):
        self.calls += 1
        if self.calls <= self._fail_attempts:
            return {"ok": False, "error_summary": f"fail-{self.calls}"}
        return {"ok": True}


class _Registry:
    def __init__(self, adapters):
        self._adapters = dict(adapters)

    def get(self, step_type: str):
        return self._adapters[step_type]

    def recovery(self, action_type: str):
        raise KeyError(action_type)


class TestRunnerRetryPolicy(unittest.TestCase):
    def setUp(self):
        self.run_dir = Path("/tmp/ael_runner_retry_policy_test")
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def tearDown(self):
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_default_retry_budget_for_check(self):
        # No policy provided: check.* defaults to budget=2 (3 attempts total).
        flaky = _FlakyAdapter(fail_attempts=2)
        plan = {
            "steps": [
                {"name": "c1", "type": "check.noop"},
            ]
        }
        res = runner.run_plan(plan, self.run_dir, _Registry({"check.noop": flaky}))
        self.assertTrue(res.get("ok"))
        self.assertEqual(flaky.calls, 3)
        self.assertEqual(res["steps"][-1].get("effective_retry_budget"), 2)

    def test_plan_retry_policy_applies(self):
        # Plan can reduce retries to 0 for check.*.
        flaky = _FlakyAdapter(fail_attempts=1)
        plan = {
            "recovery_policy": {"retries": {"check": 0}},
            "steps": [
                {"name": "c1", "type": "check.noop"},
            ],
        }
        res = runner.run_plan(plan, self.run_dir, _Registry({"check.noop": flaky}))
        self.assertFalse(res.get("ok"))
        self.assertEqual(flaky.calls, 1)
        self.assertEqual(res["steps"][-1].get("effective_retry_budget"), 0)

    def test_step_retry_budget_overrides_plan(self):
        flaky = _FlakyAdapter(fail_attempts=2)
        plan = {
            "recovery_policy": {"retries": {"check": 0}},
            "steps": [
                {"name": "c1", "type": "check.noop", "retry_budget": 2},
            ],
        }
        res = runner.run_plan(plan, self.run_dir, _Registry({"check.noop": flaky}))
        self.assertTrue(res.get("ok"))
        self.assertEqual(flaky.calls, 3)
        self.assertEqual(res["steps"][-1].get("effective_retry_budget"), 2)

    def test_load_uses_run_alias_when_load_missing(self):
        flaky = _FlakyAdapter(fail_attempts=1)
        plan = {
            "recovery_policy": {"retries": {"run": 1}},
            "steps": [
                {"name": "l1", "type": "load.noop"},
            ],
        }
        res = runner.run_plan(plan, self.run_dir, _Registry({"load.noop": flaky}))
        self.assertTrue(res.get("ok"))
        self.assertEqual(flaky.calls, 2)
        self.assertEqual(res["steps"][-1].get("effective_retry_budget"), 1)


if __name__ == "__main__":
    unittest.main()
