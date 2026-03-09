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
        }
    }

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
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        selected_ssid="ESP32_GPIO_METER_E7F1",
    )
    lkg = pipeline._build_last_known_good_setup(
        run_id="run1",
        board_cfg={"name": "ESP32-C6 DevKit"},
        test_path="tests/plans/esp32c6_gpio_signature_with_meter.json",
        flash_info=flash_info,
        instrument_id="esp32s3_dev_c_meter",
        instrument_host="192.168.4.1",
        instrument_port=9000,
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        selected_ssid="ESP32_GPIO_METER_E7F1",
        test_raw=test_raw,
        result=result,
    )
    current_setup = pipeline._build_current_setup(
        flash_info=flash_info,
        instrument_id="esp32s3_dev_c_meter",
        instrument_host="192.168.4.1",
        instrument_port=9000,
        probe_instance_id="esp32jtag_stm32_golden",
        probe_type="esp32jtag",
        probe_host="192.168.2.98",
        probe_port=4242,
        selected_ssid="ESP32_GPIO_METER_E7F1",
    )

    assert summary["board"] == "ESP32-C6 DevKit"
    assert summary["test"] == "esp32c6_gpio_signature_with_meter"
    assert summary["serial_or_flash_port"] == "/dev/ttyACM0"
    assert summary["instrument_profile"] == "esp32s3_dev_c_meter"
    assert summary["probe_instance"] == "esp32jtag_stm32_golden"
    assert summary["probe_type"] == "esp32jtag"
    assert summary["probe_endpoint"] == "192.168.2.98:4242"
    assert summary["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert summary["cleanup_items"] == ["pre-flight skipped by configuration"]
    assert summary["key_checks_passed"] == ["uart.verify", "instrument.signature"]

    assert lkg["board"] == "ESP32-C6 DevKit"
    assert lkg["port"] == "/dev/ttyACM0"
    assert lkg["probe_instance"] == "esp32jtag_stm32_golden"
    assert lkg["probe_endpoint"] == "192.168.2.98:4242"
    assert lkg["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert "X1(GPIO4) -> GPIO11 toggle @1000Hz" in lkg["wiring_assumptions"]
    assert "3V3 -> ADC GPIO4 2.8V..3.45V" in lkg["wiring_assumptions"]
    assert "GND -> GND" in lkg["wiring_assumptions"]

    assert current_setup["serial_or_flash_port"] == "/dev/ttyACM0"
    assert current_setup["instrument_profile"] == "esp32s3_dev_c_meter"
    assert current_setup["probe_instance"] == "esp32jtag_stm32_golden"
    assert current_setup["probe_endpoint"] == {"host": "192.168.2.98", "port": 4242}
    assert current_setup["selected_ap_ssid"] == "ESP32_GPIO_METER_E7F1"
    assert current_setup["selected_endpoint"] == {"host": "192.168.4.1", "port": 9000}
