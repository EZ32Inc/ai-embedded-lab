from ael.connection_model import normalize_connection_context, parse_wiring_override, resolve_bench_setup


def test_parse_wiring_override_parses_pairs_and_ignores_noise():
    assert parse_wiring_override("verify=P0.0 swd=P3 junk reset=NC") == {
        "verify": "P0.0",
        "swd": "P3",
        "reset": "NC",
    }


def test_resolve_bench_setup_prefers_bench_setup_and_falls_back_to_legacy_connections():
    assert resolve_bench_setup({"bench_setup": {"ground_required": True}, "connections": {"ground_required": False}}) == {
        "ground_required": True
    }
    assert resolve_bench_setup({"connections": {"dut_to_instrument": [{"inst_gpio": 11}]}}) == {
        "dut_to_instrument": [{"inst_gpio": 11}]
    }


def test_normalize_connection_context_merges_wiring_and_required_keys():
    ctx = normalize_connection_context(
        {"default_wiring": {"swd": "P3"}, "observe_map": {"sig": "P0.0"}},
        {},
        wiring="verify=P0.0",
        required_wiring=["swd", "reset", "verify"],
    )
    assert ctx.default_wiring == {"swd": "P3"}
    assert ctx.resolved_wiring == {"swd": "P3", "verify": "P0.0", "reset": "UNKNOWN"}
    assert "missing coarse wiring: reset" in ctx.warnings


def test_normalize_connection_context_captures_board_and_plan_shapes():
    ctx = normalize_connection_context(
        {
            "bench_connections": [{"from": "PA4", "to": "P0.0"}, {"from": "PC13", "to": "LED"}],
            "observe_map": {"sig": "P0.0"},
            "verification_views": {"signal": {"pin": "sig", "resolved_to": "P0.0"}},
        },
        {
            "bench_setup": {
                "dut_to_instrument": [{"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle"}],
                "ground_required": True,
                "ground_confirmed": True,
            }
        },
    )
    assert ctx.bench_connections == [{"from": "PA4", "to": "P0.0"}, {"from": "PC13", "to": "LED"}]
    assert ctx.bench_setup["dut_to_instrument"][0]["inst_gpio"] == 11
    assert ctx.observe_map["sig"] == "P0.0"
    assert ctx.verification_views["signal"]["resolved_to"] == "P0.0"
    assert not any("ground_confirmed" in warning for warning in ctx.warnings)


def test_normalize_connection_context_warns_on_duplicate_observation_points():
    ctx = normalize_connection_context(
        {
            "default_wiring": {"swd": "P3", "reset": "NC", "verify": "P0.0"},
            "bench_connections": [{"from": "PC13", "to": "P0.3"}, {"from": "PC13", "to": "LED"}],
        },
        {},
        required_wiring=["swd", "reset", "verify"],
    )
    assert any("MCU pin PC13 is connected to 2 observation points" in warning for warning in ctx.warnings)


def test_normalize_connection_context_warns_when_ground_required_but_not_confirmed():
    ctx = normalize_connection_context(
        {},
        {"bench_setup": {"ground_required": True}},
    )
    assert "bench_setup requires ground, but ground_confirmed is not true" in ctx.warnings
