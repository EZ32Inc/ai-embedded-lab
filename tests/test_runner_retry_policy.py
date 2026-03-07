import shutil
import time
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


class _RecoveryAdapter:
    def execute(self, action, plan, ctx):
        return {"ok": True, "action_type": action.get("type", "")}


class _FailOnceWithRecoveryHintAdapter:
    def __init__(self):
        self.calls = 0

    def execute(self, step, plan, ctx):
        self.calls += 1
        if self.calls == 1:
            return {
                "ok": False,
                "error_summary": "need reset",
                "failure_kind": "verification_miss",
                "recovery_hint": {
                    "kind": "verification_miss",
                    "recoverable": True,
                    "preferred_action": "control.reset.serial",
                    "action_type": "control.reset.serial",
                    "reason": "unit_test",
                    "scope": "step",
                    "retry": True,
                    "params": {"port": "/dev/ttyFAKE0"},
                },
            }
        return {"ok": True}


class _RegistryWithRecovery(_Registry):
    def __init__(self, adapters, recovery_adapters):
        super().__init__(adapters)
        self._recovery_adapters = dict(recovery_adapters)

    def recovery(self, action_type: str):
        return self._recovery_adapters[action_type]


class _SleepAdapter:
    def __init__(self, sleep_s: float, ok: bool = True):
        self.sleep_s = float(sleep_s)
        self.ok = bool(ok)

    def execute(self, step, plan, ctx):
        time.sleep(self.sleep_s)
        return {"ok": self.ok, "error_summary": "" if self.ok else "sleep-fail"}


class _FailOnceWithoutHintUartAdapter:
    def __init__(self):
        self.calls = 0

    def execute(self, step, plan, ctx):
        self.calls += 1
        if self.calls == 1:
            return {"ok": False, "failure_kind": "verification_miss", "error_summary": "missing expect"}
        return {"ok": True}


class _AlwaysFailWithHintAdapter:
    def __init__(self):
        self.calls = 0

    def execute(self, step, plan, ctx):
        self.calls += 1
        return {
            "ok": False,
            "failure_kind": "verification_miss",
            "error_summary": f"still failing {self.calls}",
            "recovery_hint": {
                "kind": "verification_miss",
                "recoverable": True,
                "preferred_action": "reset.serial",
                "action_type": "reset.serial",
                "reason": "limit-test",
                "scope": "step",
                "retry": True,
                "params": {"port": "/dev/ttyFAKE0"},
            },
        }


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

    def test_runner_sets_pass_termination(self):
        flaky = _FlakyAdapter(fail_attempts=0)
        plan = {"steps": [{"name": "c1", "type": "check.noop"}]}
        res = runner.run_plan(plan, self.run_dir, _Registry({"check.noop": flaky}))
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("termination"), "pass")

    def test_timeout_termination_when_run_exceeds_timeout(self):
        sleepy = _SleepAdapter(sleep_s=0.06, ok=True)
        plan = {
            "timeout_s": 0.01,
            "steps": [
                {"name": "c1", "type": "check.noop"},
                {"name": "c2", "type": "check.noop"},
            ],
        }
        res = runner.run_plan(plan, self.run_dir, _Registry({"check.noop": sleepy}))
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("termination"), "timeout")
        self.assertEqual(res.get("error_summary"), "run timeout reached")

    def test_recovery_action_alias_allowed_by_legacy_policy(self):
        adapter = _FailOnceWithRecoveryHintAdapter()
        registry = _RegistryWithRecovery(
            {"check.noop": adapter},
            {
                "control.reset.serial": _RecoveryAdapter(),
                "reset.serial": _RecoveryAdapter(),
            },
        )
        plan = {
            "steps": [{"name": "c1", "type": "check.noop", "retry_budget": 0}],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 1}},
        }
        res = runner.run_plan(plan, self.run_dir, registry)
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(res.get("recovery", [])), 1)
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertEqual(res["recovery"][0].get("action_type"), "control.reset.serial")

    def test_policy_synthesizes_uart_recovery_hint_when_missing(self):
        adapter = _FailOnceWithoutHintUartAdapter()
        registry = _RegistryWithRecovery(
            {"check.uart_log": adapter},
            {"reset.serial": _RecoveryAdapter(), "control.reset.serial": _RecoveryAdapter()},
        )
        plan = {
            "steps": [
                {
                    "name": "u1",
                    "type": "check.uart_log",
                    "retry_budget": 0,
                    "inputs": {"observe_uart_cfg": {"port": "/dev/ttyFAKE0", "baud": 115200}},
                }
            ],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 1}},
        }
        res = runner.run_plan(plan, self.run_dir, registry)
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(res.get("recovery", [])), 1)
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertEqual(res["recovery"][0].get("action_type"), "reset.serial")

    def test_serial_reset_recovery_is_capped_to_one_attempt(self):
        adapter = _AlwaysFailWithHintAdapter()
        registry = _RegistryWithRecovery(
            {"check.noop": adapter},
            {"reset.serial": _RecoveryAdapter(), "control.reset.serial": _RecoveryAdapter()},
        )
        plan = {
            "steps": [{"name": "c1", "type": "check.noop", "retry_budget": 0}],
            "recovery_policy": {"enabled": True, "allowed_actions": ["reset.serial"], "retries": {"check": 2}},
        }
        res = runner.run_plan(plan, self.run_dir, registry)
        self.assertFalse(res.get("ok"))
        self.assertEqual(len(res.get("recovery", [])), 2)
        self.assertTrue(res["recovery"][0].get("ok"))
        self.assertFalse(res["recovery"][1].get("ok"))
        self.assertIn("attempt limit reached", res["recovery"][1].get("result", {}).get("error_summary", ""))


if __name__ == "__main__":
    unittest.main()
