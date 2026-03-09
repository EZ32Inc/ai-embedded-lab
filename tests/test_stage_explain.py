from pathlib import Path

from ael import stage_explain


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_explain_plan_for_stm32f401():
    payload = stage_explain.explain_stage('stm32f401rct6', 'tests/plans/gpio_signature.json', 'plan', REPO_ROOT)
    assert payload['ok'] is True
    assert payload['stage'] == 'plan'
    assert payload['selected']['builder_kind'] == 'arm_debug'
    assert payload['selected']['board_clock_hz'] == 16000000
    assert payload['selected']['check_model'] == 'signal_verify'
    assert payload['selected']['verification_views']['signal']['resolved_to'] == 'P0.0'
    assert payload['selected']['verification_views']['led']['resolved_to'] == 'P0.3'
    assert payload['selected']['probe'] == 'configs/instrument_instances/esp32jtag_stm32_golden.yaml'
    assert payload['selected']['probe_instance'] == 'esp32jtag_stm32_golden'
    assert payload['selected']['probe_type'] == 'esp32jtag'


def test_explain_plan_for_rp2040_uses_board_probe_config():
    payload = stage_explain.explain_stage('rp2040_pico', 'tests/plans/gpio_signature.json', 'plan', REPO_ROOT)
    assert payload['ok'] is True
    assert payload['selected']['probe'] == 'configs/instrument_instances/esp32jtag_rp2040_lab.yaml'
    assert payload['selected']['probe_instance'] == 'esp32jtag_rp2040_lab'


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
