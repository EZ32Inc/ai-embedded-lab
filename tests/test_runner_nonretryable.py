from pathlib import Path

from ael.runner import run_plan


class _FailOnceAdapter:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def execute(self, step, plan, ctx):
        self.calls += 1
        return dict(self.payload)


class _Registry:
    def __init__(self, adapter):
        self.adapter = adapter

    def get(self, kind):
        return self.adapter

    def recovery(self, action_type):
        raise KeyError(action_type)


def test_runner_stops_retrying_when_step_marks_failure_nonretryable(tmp_path):
    adapter = _FailOnceAdapter({"ok": False, "error_summary": "terminal load failure", "retryable": False})
    plan = {
        "steps": [{"name": "load", "type": "load.gdbmi"}],
    }

    result = run_plan(plan, Path(tmp_path), _Registry(adapter))

    assert result["ok"] is False
    assert adapter.calls == 1
    assert len(result["steps"]) == 1
    assert result["error_summary"] == "terminal load failure"


def test_runner_retries_when_failure_is_retryable_by_default(tmp_path):
    adapter = _FailOnceAdapter({"ok": False, "error_summary": "retry me"})
    plan = {
        "steps": [{"name": "load", "type": "load.gdbmi"}],
    }

    result = run_plan(plan, Path(tmp_path), _Registry(adapter))

    assert result["ok"] is False
    assert adapter.calls == 3
    assert len(result["steps"]) == 3
