from ael import pipeline


def test_normalize_until_stage_aliases():
    assert pipeline._normalize_until_stage(None) == "report"
    assert pipeline._normalize_until_stage("preflight") == "pre-flight"
    assert pipeline._normalize_until_stage("pre-flight") == "pre-flight"
    assert pipeline._normalize_until_stage("plan") == "plan"
    assert pipeline._normalize_until_stage("report") == "report"
    assert pipeline._normalize_until_stage("unknown") == "report"


def test_filter_plan_steps_by_stage():
    steps = [
        {"name": "preflight", "type": "preflight.probe"},
        {"name": "build", "type": "build.idf"},
        {"name": "load", "type": "load.idf_esptool"},
        {"name": "check_signal", "type": "check.signal"},
    ]
    assert pipeline._filter_plan_steps_by_stage(steps, "plan") == []
    preflight_only = pipeline._filter_plan_steps_by_stage(steps, "pre-flight")
    assert len(preflight_only) == 1
    assert preflight_only[0]["type"] == "preflight.probe"
    assert pipeline._filter_plan_steps_by_stage(steps, "report") == steps


def test_stage_execution_summary():
    plan_only = pipeline._stage_execution_summary("plan")
    assert plan_only["executed"] == ["plan", "report"]
    assert "pre-flight" in plan_only["deferred"]
    preflight = pipeline._stage_execution_summary("pre-flight")
    assert preflight["executed"] == ["plan", "pre-flight", "report"]
    assert "run" in preflight["deferred"]
    full = pipeline._stage_execution_summary("report")
    assert full["deferred"] == []
