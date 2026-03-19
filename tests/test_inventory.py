import json
import os
import subprocess
import sys
from pathlib import Path

from ael import inventory


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_inventory_includes_key_duts_and_mcus():
    payload = inventory.build_inventory(REPO_ROOT)
    assert payload["ok"] is True
    assert "esp32c6_devkit" in payload["summary"]["duts_with_tests"]
    assert "rp2040_pico" in payload["summary"]["duts_with_tests"]
    assert "rp2350_pico2" in payload["summary"]["duts_with_tests"]
    assert "stm32f401rct6" in payload["summary"]["duts_with_tests"]
    assert "esp32c6" in payload["summary"]["mcus_with_tests"]
    assert "rp2040" in payload["summary"]["mcus_with_tests"]
    assert "rp2350" in payload["summary"]["mcus_with_tests"]
    assert "stm32f401rct6" in payload["summary"]["mcus_with_tests"]


def test_build_inventory_includes_pack_linked_stm32_test_and_no_missing_smoke_ref():
    payload = inventory.build_inventory(REPO_ROOT)
    stm32 = next(item for item in payload["duts"] if item["dut_id"] == "stm32f103_gpio")
    assert any(test["name"] == "stm32f103_gpio_signature" and any(source["via"] == "pack" for source in test["sources"]) for test in stm32["tests"])
    rp2040 = next(item for item in payload["duts"] if item["dut_id"] == "rp2040_pico")
    assert not any(test["path"] == "tests/plans/uart_banner.json" for test in rp2040["tests"])


def test_inventory_pack_index_resolves_extends_for_stm32f103rct6_mailbox_pilot():
    packs = inventory._load_pack_index(REPO_ROOT)
    esp = next(item for item in packs if item["path"] == "packs/smoke_stm32f103rct6_mailbox_esp32jtag.json")
    stlink = next(item for item in packs if item["path"] == "packs/smoke_stm32f103rct6_mailbox_stlink.json")
    assert esp["board"] == "stm32f103rct6"
    assert stlink["board"] == "stm32f103rct6_stlink"
    assert esp["tests"] == ["tests/plans/stm32f103rct6_mailbox.json"]
    assert stlink["tests"] == ["tests/plans/stm32f103rct6_mailbox.json"]


def test_inventory_cli_json_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "inventory", "list"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert "esp32c3_devkit" in payload["summary"]["duts_with_tests"]


def test_inventory_text_render_omits_generic_section():
    payload = inventory.build_inventory(REPO_ROOT)
    text = inventory.render_text(payload)
    assert "generic_tests" not in text
    assert "stm32f103_gpio_signature" in text
    assert "stm32f103_uart_banner" in text
    assert "rp2040_gpio_signature" in text


def test_inventory_instances_cli_json_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "inventory", "instances"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert any(item["id"] == "esp32jtag_stm32_golden" for item in payload["control_instrument_instances"])
    assert any(item["id"] == "esp32s3_dev_c_meter" for item in payload["instruments"])
    assert all(not item["metadata_validation_errors"] for item in payload["control_instrument_instances"])
    assert any(item["id"] == "esp32jtag_stm32_golden" for item in payload["compatibility"]["probe_instances"])


def test_build_instrument_instance_inventory_includes_references():
    payload = inventory.build_instrument_instance_inventory(REPO_ROOT)
    probe = next(item for item in payload["control_instrument_instances"] if item["id"] == "esp32jtag_stm32_golden")
    meter = next(item for item in payload["instruments"] if item["id"] == "esp32s3_dev_c_meter")
    assert payload["summary"]["control_instrument_instance_count"] >= 1
    assert probe["kind"] == "control_instrument_instance"
    assert "stm32f103_gpio" in probe["referenced_by"]["boards"]
    assert "stm32f401rct6" in probe["referenced_by"]["boards"]
    assert "esp32c6_gpio_signature_with_meter.json" in " ".join(meter["referenced_by"]["plans"])
    assert probe["metadata_validation_errors"] == []
    assert meter["metadata_validation_errors"] == []


def test_describe_test_for_stm32f401_gpio_signature():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/stm32f401_gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "stm32f401rct6"
    assert payload["selected_dut"]["runtime_binding"] == "board_profile_driven"
    assert payload["selected_board_profile"]["id"] == "stm32f401rct6"
    assert payload["selected_board_profile"]["config"] == "configs/boards/stm32f401rct6.yaml"
    assert payload["selected_board_profile"]["role"] == "runtime_policy"
    assert payload["selected_instrument"]["kind"] == "control_instrument"
    assert payload["selected_instrument"]["legacy_kind"] == "probe"
    assert payload["selected_instrument"]["id"] == "esp32jtag_stm32_golden"
    assert payload["selected_instrument"]["communication"]["primary"] == "gdb_remote"
    assert payload["compatibility"]["probe_or_instrument"]["kind"] == "control_instrument"
    assert payload["selected_bench_resources"]["resource_keys"] == ["probe:192.168.2.98:4242"]
    assert payload["selected_bench_resources"]["contract_version"] == 1
    assert "control_instrument_id:esp32jtag_stm32_golden" in payload["selected_bench_resources"]["selection_digest"]
    assert payload["selected_bench_resources"]["resource_summary"]["control_instrument_endpoints"] == ["192.168.2.98:4242"]
    assert payload["compatibility"]["probe_or_instrument"]["legacy_kind"] == "probe"
    assert any(conn["from"] == "SWD" and conn["to"] == "P3" for conn in payload["connections"])
    assert any(conn["from"] == "PA4" and conn["to"] == "P0.0" for conn in payload["connections"])
    assert any(conn["from"] == "PA3" and conn["to"] == "P0.1" for conn in payload["connections"])
    assert any(conn["from"] == "PA2" and conn["to"] == "P0.2" for conn in payload["connections"])
    assert any(conn["from"] == "PC13" and conn["to"] == "P0.3" for conn in payload["connections"])
    assert any(conn["from"] == "PC13" and conn["to"] == "LED" for conn in payload["connections"])
    assert len(payload["warnings"]) == 1
    assert "MCU pin PC13 is connected to 2 observation points" in payload["warnings"][0]
    assert payload["board_context"]["clock_hz"] == 16000000
    assert payload["board_context"]["verification_views"]["signal"]["resolved_to"] == "P0.0"
    assert payload["connection_setup"]["resolved_wiring"]["verify"] == "P0.0"
    assert payload["connection_setup"]["verification_views"]["signal"]["resolved_to"] == "P0.0"
    assert payload["selected_bench_resources"]["selected_instrument"]["id"] == "esp32jtag_stm32_golden"
    assert any(item.startswith("wiring:") for item in payload["selected_bench_resources"]["connection_digest"])
    assert any(check["type"] == "signal" for check in payload["expected_checks"])
    rendered = inventory.render_describe_text(payload)
    assert "selected_dut: stm32f401rct6" in rendered
    assert "selected_board_profile: stm32f401rct6" in rendered
    assert "dut_runtime_binding: board_profile_driven" in rendered
    assert "board_profile_role: runtime_policy" in rendered
    assert "bench_resource_contract_version: 1" in rendered
    assert "bench_resource_selection_digest: control_instrument_id:esp32jtag_stm32_golden; control_instrument_endpoint:192.168.2.98:4242" in rendered
    assert "board_profile_config: configs/boards/stm32f401rct6.yaml" in rendered
    assert "control_instrument: esp32jtag_stm32_golden" in rendered
    assert "legacy_kind: probe" in rendered
    assert "connection_setup:" in rendered
    assert "source_summary:" in rendered
    assert "resolved_wiring:" in rendered
    assert "verification_views:" in rendered


def test_describe_test_warns_on_duplicate_mcu_pin_connections():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/stm32f401_gpio_signature.json", REPO_ROOT)
    assert len(payload["warnings"]) == 1
    assert "MCU pin PC13 is connected to 2 observation points" in payload["warnings"][0]
    assert payload["connection_setup"]["warnings"]


def test_describe_test_for_meter_path():
    payload = inventory.describe_test("esp32c6_devkit", "tests/plans/esp32c6_gpio_signature_with_meter.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "esp32c6_devkit"
    assert payload["selected_dut"]["runtime_binding"] == "board_profile_driven"
    assert payload["selected_board_profile"]["config"] == "configs/boards/esp32c6_devkit.yaml"
    assert payload["selected_board_profile"]["role"] == "runtime_policy"
    assert payload["selected_instrument"]["kind"] == "instrument"
    assert payload["selected_instrument"]["id"] == "esp32s3_dev_c_meter"
    assert payload["selected_bench_resources"]["selected_instrument"]["id"] == "esp32s3_dev_c_meter"
    assert payload["selected_bench_resources"]["contract_version"] == 1
    assert "instrument_id:esp32s3_dev_c_meter" in payload["selected_bench_resources"]["selection_digest"]
    assert "compatibility" not in payload or "probe_or_instrument" not in payload.get("compatibility", {})
    assert any(conn["from"] == "X1(GPIO4)" and conn["to"] == "inst GPIO11" for conn in payload["connections"])
    assert any(check["type"] == "instrument_measure" for check in payload["expected_checks"])
    rendered = inventory.render_describe_text(payload)
    assert "ground_required: True" in rendered
    assert "ground_confirmed: True" in rendered


def test_describe_test_for_rp2350_gpio_signature():
    payload = inventory.describe_test("rp2350_pico2", "tests/plans/rp2350_gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "rp2350_pico2"
    assert payload["selected_dut"]["runtime_binding"] == "board_profile_driven"
    assert payload["selected_board_profile"]["id"] == "rp2350_pico2"
    assert payload["selected_board_profile"]["config"] == "configs/boards/rp2350_pico2.yaml"
    assert payload["selected_board_profile"]["role"] == "runtime_policy"
    assert payload["selected_instrument"]["kind"] == "control_instrument"
    assert payload["selected_instrument"]["id"] == "esp32jtag_rp2040_lab"
    assert any(conn["from"] == "GPIO16" and conn["to"] == "P0.0" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "selected_dut: rp2350_pico2" in rendered
    assert "selected_board_profile: rp2350_pico2" in rendered


def test_describe_test_for_rp2350_uart_banner():
    payload = inventory.describe_test("rp2350_pico2", "tests/plans/rp2350_uart_banner.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "rp2350_pico2"
    assert payload["connection_setup"]["bench_setup"]["serial_console"]["port"] == "/dev/ttyACM0"
    assert any(conn["from"] == "host serial" and conn["to"] == "/dev/ttyACM0" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "host serial -> /dev/ttyACM0" in rendered


def test_describe_test_for_rp2350_gpio_signature_contract():
    payload = inventory.describe_test("rp2350_pico2", "tests/plans/rp2350_gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["connection_setup"]["bench_setup"]["serial_console"]["port"] == "not_used"
    rendered = inventory.render_describe_text(payload)
    assert "host serial -> not_used" in rendered


def test_describe_test_for_generated_rp2040_adc_contract():
    payload = inventory.describe_test("rp2040_pico", "tests/plans/rp2040_adc_banner.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["connection_setup"]["bench_setup"]["serial_console"]["port"] == "/dev/ttyACM0"
    assert payload["connection_setup"]["bench_setup"]["peripheral_signals"][0]["dut_signal"] == "GPIO26/ADC0"
    assert payload["connection_setup"]["bench_setup"]["external_inputs"][0]["status"] == "not_defined"
    assert any(conn["from"] == "host serial" and conn["to"] == "/dev/ttyACM0" for conn in payload["connections"])
    assert any(conn["from"] == "ADC0" and conn["to"] == "GPIO26/ADC0" for conn in payload["connections"])
    assert any(conn["to"] == "GPIO26/ADC0" and conn.get("status") == "not_defined" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "host serial -> /dev/ttyACM0" in rendered
    assert "ADC0 -> GPIO26/ADC0" in rendered
    assert "UNSPECIFIED_ANALOG_SOURCE -> GPIO26/ADC0" in rendered


def test_describe_test_for_generated_stm32_spi_contract():
    payload = inventory.describe_test("stm32f103_gpio", "tests/plans/stm32f103_spi_banner.json", REPO_ROOT)
    assert payload["ok"] is True
    bench_setup = payload["connection_setup"]["bench_setup"]
    assert "serial_console" not in bench_setup
    assert bench_setup["external_inputs"][0]["source"] == "SPI_LOOPBACK"
    assert any(conn["from"] == "SPI1_SCK" and conn["to"] == "PA5" for conn in payload["connections"])
    assert any(conn["from"] == "SPI_LOOPBACK" and conn["to"] == "PA6/SPI1_MISO" for conn in payload["connections"])
    rendered = inventory.render_connection_text(
        inventory.describe_connection("stm32f103_gpio", "tests/plans/stm32f103_spi_banner.json", REPO_ROOT)
    )
    assert "SPI1_SCK -> PA5" in rendered
    assert "SPI_LOOPBACK -> PA6/SPI1_MISO" in rendered


def test_describe_test_for_generated_stm32_uart_dual_instrument_contract():
    payload = inventory.describe_test("stm32f103_uart", "tests/plans/stm32f103_uart_banner.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "stm32f103_uart"
    assert payload["selected_board_profile"]["id"] == "stm32f103_uart"
    assert payload["selected_instrument"]["id"] == "esp32jtag_stm32_uart"
    bench_setup = payload["connection_setup"]["bench_setup"]
    assert bench_setup["serial_console"]["port"] == "/dev/ttyUSB0"
    assert bench_setup["instrument_roles"][0]["instrument_id"] == "esp32jtag_stm32_uart"
    assert bench_setup["instrument_roles"][1]["instrument_id"] == "usb_uart_bridge_daemon"
    assert any(conn["from"] == "uart_tx" and conn["to"] == "PA9/USART1_TX" for conn in payload["connections"])
    assert any(conn["from"] == "control_instrument" and conn["to"] == "esp32jtag_stm32_uart" for conn in payload["connections"])
    assert any(conn["from"] == "uart_instrument" and conn["to"] == "usb_uart_bridge_daemon" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "uart_tx -> PA9/USART1_TX" in rendered
    assert "control_instrument -> esp32jtag_stm32_uart" in rendered
    assert "uart_instrument -> usb_uart_bridge_daemon" in rendered


def test_describe_test_for_generated_esp32_i2c_contract():
    payload = inventory.describe_test("esp32c6_devkit", "tests/plans/esp32c6_i2c_banner.json", REPO_ROOT)
    assert payload["ok"] is True
    assert any(conn["from"] == "I2C0_SDA" and conn["to"] == "GPIO8" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "I2C0_SDA -> GPIO8" in rendered


def test_describe_connection_for_meter_path():
    payload = inventory.describe_connection("esp32c6_devkit", "tests/plans/esp32c6_gpio_signature_with_meter.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["source_summary"]["bench_setup"] == "test.bench_setup"
    assert payload["connection_setup"]["bench_setup"]["ground_confirmed"] is True
    assert payload["validation_errors"] == []
    text = inventory.render_connection_text(payload)
    assert "connection_setup:" in text
    assert "resolved_wiring:" in text
    assert "ground_confirmed: True" in text
    assert "X1(GPIO4) -> inst GPIO11" in text


def test_inventory_describe_connection_cli_text_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "inventory", "describe-connection", "--board", "esp32c6_devkit", "--test", "tests/plans/esp32c6_gpio_signature_with_meter.json", "--format", "text"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "connection_setup:" in res.stdout
    assert "ground_confirmed: True" in res.stdout


def test_inventory_diff_connection_cli_text_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "ael",
            "inventory",
            "diff-connection",
            "--board",
            "rp2040_pico",
            "--test",
            "tests/plans/rp2040_gpio_signature.json",
            "--against-board",
            "stm32f103",
            "--against-test",
            "tests/plans/stm32f103_gpio_signature.json",
            "--format",
            "text",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "left_only:" in res.stdout
    assert "right_only:" in res.stdout


def test_describe_test_for_stm32f103_gpio_signature_multi_signal_contract():
    payload = inventory.describe_test("stm32f103_gpio", "tests/plans/stm32f103_gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    checks = payload["expected_checks"]
    assert any(check["type"] == "signal" and check["pin"] == "pa4" for check in checks)
    assert any(check["type"] == "signal" and check["pin"] == "pa5" for check in checks)
    assert any(
        check["type"] == "frequency_ratio"
        and check.get("numerator") == "pa4_fast"
        and check.get("denominator") == "pa5_half_rate"
        for check in checks
    )
    assert any(conn["from"] == "PA4" and conn["to"] == "P0.0" for conn in payload["connections"])
    assert any(conn["from"] == "PA5" and conn["to"] == "P0.1" for conn in payload["connections"])
    rendered = inventory.render_describe_text(payload)
    assert "frequency_ratio: pa4_fast/pa5_half_rate min=1.8 max=2.2" in rendered


def test_describe_test_for_stm32f401_led_blink():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/stm32f401_led_blink.json", REPO_ROOT)
    assert payload["ok"] is True
    assert any(conn["from"] == "PC13" and conn["to"] == "P0.3" for conn in payload["connections"])
    assert any(conn["from"] == "PC13" and conn["to"] == "LED" for conn in payload["connections"])
    assert any(check["type"] == "led" and check["pin"] == "led" for check in payload["expected_checks"])
    assert any(check["type"] == "signal" and check["pin"] == "led" for check in payload["expected_checks"])
