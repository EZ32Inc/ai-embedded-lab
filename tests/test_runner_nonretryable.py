import json
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


def test_runner_cleans_up_managed_local_stlink_server_after_plan(tmp_path):
    artifacts = Path(tmp_path) / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    state_path = artifacts / "runtime_state.json"
    state_path.write_text(json.dumps({"managed_local_stlink_server": {"managed": True, "pid": 1234}}), encoding="utf-8")

    adapter = _FailOnceAdapter({"ok": True})
    plan = {"steps": [{"name": "load", "type": "load.gdbmi"}]}

    from unittest.mock import patch
    with patch("ael.runner.flash_bmda_gdbmi._cleanup_managed_local_stlink_server") as cleanup:
        result = run_plan(plan, Path(tmp_path), _Registry(adapter))

    assert result["ok"] is True
    cleanup.assert_called_once_with({"managed": True, "pid": 1234}, print)
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert "managed_local_stlink_server" not in saved
