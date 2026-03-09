from ael import pipeline


def test_filter_plan_steps_by_run_excludes_check_steps():
    steps = [
        {"name": "preflight", "type": "preflight.probe"},
        {"name": "build", "type": "build.arm_debug"},
        {"name": "load", "type": "load.gdbmi"},
        {"name": "check_signal", "type": "check.signal_verify"},
        {"name": "check_uart", "type": "check.uart_log"},
    ]

    filtered = pipeline._filter_plan_steps_by_stage(steps, "run")

    assert [step["name"] for step in filtered] == ["preflight", "build", "load"]


def test_stage_execution_summary_for_run_defers_check():
    summary = pipeline._stage_execution_summary("run", preflight_enabled=True)

    assert summary["requested_until"] == "run"
    assert summary["executed"] == ["plan", "pre-flight", "run", "report"]
    assert "check" in summary["deferred"]


def test_filter_plan_steps_by_run_exit_excludes_check_steps():
    steps = [
        {"name": "preflight", "type": "preflight.probe"},
        {"name": "build", "type": "build.arm_debug"},
        {"name": "load", "type": "load.gdbmi"},
        {"name": "check_signal", "type": "check.signal_verify"},
    ]

    filtered = pipeline._filter_plan_steps_by_stage(steps, "run-exit")

    assert [step["name"] for step in filtered] == ["preflight", "build", "load"]


def test_stage_execution_summary_for_run_exit_defers_check():
    summary = pipeline._stage_execution_summary("run-exit", preflight_enabled=True)

    assert summary["requested_until"] == "run-exit"
    assert summary["executed"] == ["plan", "pre-flight", "run", "report"]
    assert "check" in summary["deferred"]
