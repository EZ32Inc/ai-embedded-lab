from pathlib import Path

from ael import stage_explain


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_explain_plan_for_stm32f401():
    payload = stage_explain.explain_stage('stm32f401rct6', 'tests/plans/gpio_signature.json', 'plan', REPO_ROOT)
    assert payload['ok'] is True
    assert payload['stage'] == 'plan'
    assert payload["selected"]["selected_dut"]["id"] == "stm32f401rct6"
    assert payload["selected"]["selected_board_profile"]["id"] == "stm32f401rct6"
    assert payload["selected"]["selected_board_profile"]["config"] == "configs/boards/stm32f401rct6.yaml"
    assert payload['selected']['builder_kind'] == 'arm_debug'
    assert payload['selected']['board_clock_hz'] == 16000000
    assert payload['selected']['check_model'] == 'signal_verify'
    assert payload['selected']['verification_views']['signal']['resolved_to'] == 'P0.0'
    assert payload['selected']['verification_views']['led']['resolved_to'] == 'P0.3'
    assert payload['selected']['control_instrument_selection']['instance'] == 'esp32jtag_stm32_golden'
    assert payload['selected']['control_instrument_selection']['type'] == 'esp32jtag'
    assert payload['selected']['control_instrument'] == 'configs/instrument_instances/esp32jtag_stm32_golden.yaml'
    assert payload['selected']['control_instrument_instance'] == 'esp32jtag_stm32_golden'
    assert payload['selected']['control_instrument_type'] == 'esp32jtag'
    assert payload['selected']['control_instrument_communication']['primary'] == 'gdb_remote'
    assert payload['selected']['control_instrument_capability_surfaces']['swd'] == 'gdb_remote'
    assert payload['selected']['compatibility']['probe'] == 'configs/instrument_instances/esp32jtag_stm32_golden.yaml'
    assert payload['selected']['compatibility']['probe_instance'] == 'esp32jtag_stm32_golden'
    assert payload['selected']['compatibility']['probe_type'] == 'esp32jtag'
    assert payload['selected']['compatibility']['probe_communication']['primary'] == 'gdb_remote'
    assert payload['selected']['compatibility']['probe_capability_surfaces']['swd'] == 'gdb_remote'
    assert payload["selected"]["selected_bench_resources"]["control_instrument"]["instance"] == "esp32jtag_stm32_golden"
    assert any(item['capability'] == 'swd' and item['surface'] == 'gdb_remote' for item in payload['selected']['capability_surface_plan'])
    assert any(item['capability'] == 'gpio_in' and item['surface'] == 'web_api' for item in payload['selected']['capability_surface_plan'])


def test_explain_plan_for_rp2040_uses_board_probe_config():
    payload = stage_explain.explain_stage('rp2040_pico', 'tests/plans/gpio_signature.json', 'plan', REPO_ROOT)
    assert payload['ok'] is True
    assert payload["selected"]["selected_dut"]["id"] == "rp2040_pico"
    assert payload["selected"]["selected_board_profile"]["config"] == "configs/boards/rp2040_pico.yaml"
    assert payload['selected']['control_instrument_selection']['config'] == 'configs/instrument_instances/esp32jtag_rp2040_lab.yaml'
    assert payload['selected']['control_instrument_instance'] == 'esp32jtag_rp2040_lab'
    assert payload['selected']['compatibility']['probe'] == 'configs/instrument_instances/esp32jtag_rp2040_lab.yaml'
    assert payload['selected']['compatibility']['probe_instance'] == 'esp32jtag_rp2040_lab'
    assert payload['selected']['compatibility']['probe_communication']['primary'] == 'gdb_remote'
    assert payload['selected']['compatibility']['probe_capability_surfaces']['gpio_in'] == 'web_api'


def test_explain_preflight_for_meter_disabled_path():
    payload = stage_explain.explain_stage('esp32c6_devkit', 'tests/plans/esp32c6_gpio_signature_with_meter.json', 'pre-flight', REPO_ROOT)
    assert payload['ok'] is True
    assert payload['stage'] == 'pre-flight'
    assert payload['enabled'] is False
    assert payload['reason_if_skipped'] == 'pre-flight disabled by configuration'


def test_explain_check_for_meter_path_includes_uart_and_instrument():
    payload = stage_explain.explain_stage('esp32c6_devkit', 'tests/plans/esp32c6_gpio_signature_with_meter.json', 'check', REPO_ROOT)
    assert payload['ok'] is True
    assert any(item['type'] == 'uart' for item in payload['checks'])
    assert any(item['type'] == 'check.instrument_signature' for item in payload['checks'])


def test_explain_plan_for_meter_path_includes_instrument_surface_plan():
    payload = stage_explain.explain_stage('esp32c6_devkit', 'tests/plans/esp32c6_gpio_signature_with_meter.json', 'plan', REPO_ROOT)
    assert payload['ok'] is True
    assert payload["selected"]["selected_dut"]["id"] == "esp32c6_devkit"
    assert payload["selected"]["selected_board_profile"]["config"] == "configs/boards/esp32c6_devkit.yaml"
    assert payload['selected']['control_instrument_selection'] is None
    assert payload['selected']['control_instrument'] is None
    assert payload['selected']['control_instrument_instance'] is None
    assert payload['selected']['compatibility']['probe'] is None
    assert payload['selected']['compatibility']['probe_instance'] is None
    assert payload["selected"]["selected_bench_resources"]["instrument"]["id"] == "esp32s3_dev_c_meter"
    assert payload['selected']['instrument_communication']['endpoint'] == '192.168.4.1:9000'
    assert any(item['capability'] == 'measure.digital' and item['surface'] == 'primary' for item in payload['selected']['capability_surface_plan'])
    assert any(item['capability'] == 'measure.voltage' and item['surface'] == 'primary' for item in payload['selected']['capability_surface_plan'])


def test_render_text_includes_communication_blocks_readably():
    text = stage_explain.render_text(
        {
            "ok": True,
            "stage": "plan",
            "board": "stm32f401rct6",
            "test": {"name": "gpio_signature", "path": "tests/plans/gpio_signature.json"},
            "selected": {
                "selected_dut": {"id": "stm32f401rct6", "name": "STM32F401"},
                "selected_board_profile": {"id": "stm32f401rct6", "config": "configs/boards/stm32f401rct6.yaml"},
                "selected_bench_resources": {
                    "control_instrument": {"instance": "esp32jtag_stm32_golden"},
                    "connection_setup": {
                        "source_summary": {"bench_setup": "test.bench_setup"},
                        "resolved_wiring": {"verify": "P0.0"},
                    },
                },
                "control_instrument": "configs/instrument_instances/esp32jtag_stm32_golden.yaml",
                "control_instrument_communication": {"primary": "gdb_remote"},
                "control_instrument_capability_surfaces": {"swd": "gdb_remote"},
                "instrument_communication": {"transport": "wifi", "endpoint": "192.168.4.1:9000"},
                "instrument_capability_surfaces": {"measure.digital": "primary"},
                "connection_setup": {
                    "source_summary": {"bench_setup": "test.bench_setup"},
                    "resolved_wiring": {"verify": "P0.0"},
                    "verification_views": {"signal": {"pin": "sig", "resolved_to": "P0.0"}},
                    "bench_setup": {"ground_required": True, "ground_confirmed": True},
                },
                "capability_surface_plan": [{"capability": "swd", "surface": "gdb_remote"}],
            },
        }
    )
    assert "control_instrument_communication:" in text
    assert "primary: gdb_remote" in text
    assert "control_instrument_capability_surfaces:" in text
    assert "instrument_communication:" in text
    assert "instrument_capability_surfaces:" in text
    assert "selected_dut:" in text
    assert "selected_board_profile:" in text
    assert "selected_bench_resources:" in text
    assert "connection_setup:" in text
    assert "ground_confirmed: True" in text
    assert "capability_surface_plan:" in text


def test_render_text_includes_preflight_connection_setup_readably():
    text = stage_explain.render_text(
        {
            "ok": True,
            "stage": "pre-flight",
            "board": "esp32c6_devkit",
            "test": {"name": "gpio_signature", "path": "tests/plans/esp32c6_gpio_signature_with_meter.json"},
            "connection_setup": {
                "source_summary": {"bench_setup": "test.bench_setup"},
                "bench_setup": {"ground_required": True, "ground_confirmed": True},
                "warnings": [],
            },
        }
    )
    assert "connection_setup:" in text
    assert "ground_required: True" in text
