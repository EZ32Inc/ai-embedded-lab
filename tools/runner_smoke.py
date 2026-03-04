#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ael import runner


class _DummyAdapter:
    def execute(self, step, plan, ctx):
        return {"ok": True, "note": f"executed {step.get('type', '')}"}


class _DummyRegistry:
    def __init__(self):
        self._adapters = {
            "build.noop": _DummyAdapter(),
            "check.noop": _DummyAdapter(),
            "recover.noop": _DummyAdapter(),
        }

    def get(self, step_type: str):
        return self._adapters[step_type]

    def recovery(self, action_type: str):
        return self._adapters[action_type]


def main() -> int:
    run_dir = Path("/tmp/ael_runner_smoke_run")
    if run_dir.exists():
        shutil.rmtree(run_dir)

    plan = {
        "name": "runner_smoke",
        "recovery_policy": {"enabled": True, "allowed_actions": ["recover.noop"]},
        "steps": [
            {"name": "build", "type": "build.noop"},
            {"name": "check", "type": "check.noop"},
        ],
    }

    reg = _DummyRegistry()
    result = runner.run_plan(plan, run_dir, reg)

    plan_art = run_dir / "artifacts" / "run_plan.json"
    result_art = run_dir / "artifacts" / "result.json"

    assert plan_art.exists(), "missing run_plan.json"
    assert result_art.exists(), "missing result.json"
    assert bool(result.get("ok", False)), "runner returned non-ok result"

    print("[RUNNER_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
