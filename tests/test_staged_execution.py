from ael import pipeline
from ael.connection_model import build_connection_setup, normalize_connection_context, wiring_assumption_lines


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
    assert plan_only["skipped"] == []
    assert "pre-flight" in plan_only["deferred"]
    preflight = pipeline._stage_execution_summary("pre-flight")
    assert preflight["executed"] == ["plan", "pre-flight", "report"]
    assert preflight["skipped"] == []
    assert "run" in preflight["deferred"]
    full = pipeline._stage_execution_summary("report")
    assert full["deferred"] == []
    assert full["skipped"] == []


def test_stage_execution_summary_with_skipped_preflight():
    plan_only = pipeline._stage_execution_summary("plan", preflight_enabled=False)
    assert plan_only["executed"] == ["plan", "report"]
    assert plan_only["skipped"] == ["pre-flight"]
    assert plan_only["deferred"] == ["run", "check"]

    preflight = pipeline._stage_execution_summary("pre-flight", preflight_enabled=False)
    assert preflight["executed"] == ["plan", "report"]
    assert preflight["skipped"] == ["pre-flight"]
    assert preflight["deferred"] == ["run", "check"]

    full = pipeline._stage_execution_summary("report", preflight_enabled=False)
    assert full["executed"] == ["plan", "run", "check", "report"]
    assert full["skipped"] == ["pre-flight"]
    assert full["deferred"] == []


def test_success_summary_contains_validation_and_last_known_good_fields():
    result = {
        "ok": True,
        "stage_execution": {"executed": ["plan", "run", "check", "report"], "skipped": ["pre-flight"]},
        "json": {
            "run_plan": "/tmp/run_plan.json",
            "runner_result": "/tmp/artifacts/result.json",
            "evidence": "/tmp/evidence.json",
            "verify_result": "/tmp/verify_result.json",
            "uart_observe": "/tmp/uart_observe.json",
        },
    }
    evidence_payload = {
        "items": [
            {"status": "pass", "kind": "uart.verify"},
            {"status": "pass", "kind": "instrument.signature"},
        ]
    }
    flash_info = {"port": "/dev/ttyACM0"}
    test_raw = {
        "connections": {
            "dut_to_instrument": [
                {"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle", "freq_hz": 1000}
            ],
            "dut_to_instrument_analog": [
                {"dut_signal": "3V3", "inst_adc_gpio": 4, "expect_v_min": 2.8, "expect_v_max": 3.45}
            ],
            "ground_required": True,
            "ground_confirmed": True,
        }
    }
    conn_setup = build_connection_setup(normalize_connection_context({}, test_raw))
    conn_setup["wiring_assumptions"] = wiring_assumption_lines(normalize_connection_context({}, test_raw))

    summary = pipeline._build_validation_summary(
        run_id="run1",
        board_cfg={"name": "ESP32-C6 DevKit"},
        test_path="tests/plans/esp32c6_gpio_signature_with_meter.json",
        run_result_path="/tmp/result.json",
        result=result,
        flash_info=flash_info,
        evidence_payload=evidence_payload,
        instrument_id="esp32s3_dev_c_meter",
        instrument_host="192.168.4.1",
        instrument_port=9000,
        instrument_communication={"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"},
        instrument_capability_surfaces={"measure.digital": "primary"},
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        probe_communication={"primary": "gdb_remote"},
        probe_capability_surfaces={"swd": "gdb_remote"},
        selected_ssid="ESP32_GPIO_METER_E7F1",
        connection_setup=conn_setup,
    )
    lkg = pipeline._build_last_known_good_setup(
        run_id="run1",
        board_cfg={"name": "ESP32-C6 DevKit"},
        test_path="tests/plans/esp32c6_gpio_signature_with_meter.json",
        flash_info=flash_info,
        instrument_id="esp32s3_dev_c_meter",
        instrument_host="192.168.4.1",
        instrument_port=9000,
        instrument_communication={"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"},
        instrument_capability_surfaces={"measure.digital": "primary"},
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        probe_communication={"primary": "gdb_remote"},
        probe_capability_surfaces={"swd": "gdb_remote"},
        selected_ssid="ESP32_GPIO_METER_E7F1",
        connection_setup=conn_setup,
        result=result,
    )
    current_setup = pipeline._build_current_setup(
        flash_info=flash_info,
        instrument_id="esp32s3_dev_c_meter",
        instrument_host="192.168.4.1",
        instrument_port=9000,
        instrument_communication={"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"},
        instrument_capability_surfaces={"measure.digital": "primary"},
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        probe_communication={"primary": "gdb_remote"},
        probe_capability_surfaces={"swd": "gdb_remote"},
        selected_ssid="ESP32_GPIO_METER_E7F1",
        connection_setup=conn_setup,
    )

    assert summary["board"] == "ESP32-C6 DevKit"
    assert summary["test"] == "esp32c6_gpio_signature_with_meter"
    assert summary["serial_or_flash_port"] == "/dev/ttyACM0"
    assert summary["instrument_profile"] == "esp32s3_dev_c_meter"
    assert summary["instrument_communication"]["protocol"] == "gpio_meter_v1"
    assert summary["instrument_capability_surfaces"]["measure.digital"] == "primary"
    assert summary["probe_instance"] == "esp32jtag_stm32_golden"
    assert summary["probe_type"] == "esp32jtag"
    assert summary["probe_endpoint"] == "192.168.2.98:4242"
    assert summary["probe_communication"]["primary"] == "gdb_remote"
    assert summary["probe_capability_surfaces"]["swd"] == "gdb_remote"
    assert summary["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert summary["cleanup_items"] == ["pre-flight skipped by configuration"]
    assert summary["key_checks_passed"] == ["uart.verify", "instrument.signature"]
    assert summary["connection_setup"]["bench_setup"]["ground_required"] is True
    assert summary["connection_setup"]["bench_setup"]["ground_confirmed"] is True
    assert any(item.startswith("digital X1(GPIO4)->GPIO11") for item in summary["connection_digest"])

    assert lkg["board"] == "ESP32-C6 DevKit"
    assert lkg["port"] == "/dev/ttyACM0"
    assert lkg["instrument_communication"]["protocol"] == "gpio_meter_v1"
    assert lkg["instrument_capability_surfaces"]["measure.digital"] == "primary"
    assert lkg["probe_instance"] == "esp32jtag_stm32_golden"
    assert lkg["probe_endpoint"] == "192.168.2.98:4242"
    assert lkg["probe_communication"]["primary"] == "gdb_remote"
    assert lkg["probe_capability_surfaces"]["swd"] == "gdb_remote"
    assert lkg["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert "X1(GPIO4) -> GPIO11 toggle @1000Hz" in lkg["wiring_assumptions"]
    assert "3V3 -> ADC GPIO4 2.8V..3.45V" in lkg["wiring_assumptions"]
    assert "GND -> GND" in lkg["wiring_assumptions"]
    assert any(item.startswith("ground required confirmed=True") for item in lkg["connection_digest"])

    assert current_setup["serial_or_flash_port"] == "/dev/ttyACM0"
    assert current_setup["instrument_profile"] == "esp32s3_dev_c_meter"
    assert current_setup["instrument_communication"]["protocol"] == "gpio_meter_v1"
    assert current_setup["instrument_capability_surfaces"]["measure.digital"] == "primary"
    assert current_setup["probe_instance"] == "esp32jtag_stm32_golden"
    assert current_setup["probe_endpoint"] == {"host": "192.168.2.98", "port": 4242}
    assert current_setup["probe_communication"]["primary"] == "gdb_remote"
    assert current_setup["probe_capability_surfaces"]["swd"] == "gdb_remote"
    assert current_setup["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert current_setup["selected_endpoint"] == {"host": "192.168.4.1", "port": 9000}
    assert current_setup["connection_setup"]["bench_setup"]["ground_required"] is True
    assert any(item.startswith("ground required confirmed=True") for item in current_setup["connection_digest"])


def test_print_success_summary_includes_capability_surface_lines(capsys):
    summary = {
        "board": "ESP32-C6 DevKit",
        "test": "esp32c6_gpio_signature_with_meter",
        "run_id": "run1",
        "overall_result": "pass",
        "executed_stages": ["plan", "run", "check", "report"],
        "instrument_profile": "esp32s3_dev_c_meter",
        "endpoint": "192.168.4.1:9000",
        "instrument_capability_surfaces": {"measure.digital": "primary"},
        "probe_instance": "esp32jtag_stm32_golden",
        "probe_type": "esp32jtag",
        "probe_endpoint": "192.168.2.98:4242",
        "probe_capability_surfaces": {"swd": "gdb_remote"},
        "connection_digest": ["wiring: verify=P0.0"],
        "key_artifact_paths": {"result": "/tmp/result.json", "run_plan": "/tmp/run_plan.json"},
        "key_evidence_paths": {"evidence": "/tmp/evidence.json", "verify_result": "/tmp/verify.json"},
    }
    last_known_good = {
        "board": "ESP32-C6 DevKit",
        "test": "esp32c6_gpio_signature_with_meter",
        "port": "/dev/ttyACM0",
        "run_id": "run1",
        "instrument_profile": "esp32s3_dev_c_meter",
        "endpoint": "192.168.4.1:9000",
        "instrument_capability_surfaces": {"measure.digital": "primary"},
        "probe_instance": "esp32jtag_stm32_golden",
        "probe_type": "esp32jtag",
        "probe_endpoint": "192.168.2.98:4242",
        "probe_capability_surfaces": {"swd": "gdb_remote"},
        "connection_digest": ["wiring: verify=P0.0"],
        "artifact_or_evidence_location": "/tmp/evidence.json",
    }
    current_setup = {
        "selected_endpoint": {"host": "192.168.4.1", "port": 9000},
        "instrument_profile": "esp32s3_dev_c_meter",
        "probe_instance": "esp32jtag_stm32_golden",
        "probe_endpoint": {"host": "192.168.2.98", "port": 4242},
        "connection_digest": ["wiring: verify=P0.0"],
    }

    pipeline._print_success_summary(summary, last_known_good, current_setup)
    out = capsys.readouterr().out

    assert "Summary: instrument_surfaces=measure.digital->primary" in out
    assert "Summary: probe_surfaces=swd->gdb_remote" in out
    assert "Summary: connection_digest=" in out
    assert "LKG: instrument_surfaces=measure.digital->primary" in out
    assert "LKG: probe_surfaces=swd->gdb_remote" in out
    assert "LKG: connection_digest=" in out
