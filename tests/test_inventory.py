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
    assert "stm32f401rct6" in payload["summary"]["duts_with_tests"]
    assert "esp32c6" in payload["summary"]["mcus_with_tests"]
    assert "rp2040" in payload["summary"]["mcus_with_tests"]
    assert "stm32f401rct6" in payload["summary"]["mcus_with_tests"]


def test_build_inventory_includes_pack_linked_stm32_test_and_no_missing_smoke_ref():
    payload = inventory.build_inventory(REPO_ROOT)
    stm32 = next(item for item in payload["duts"] if item["dut_id"] == "stm32f103")
    assert any(test["name"] == "gpio_signature" and any(source["via"] == "pack" for source in test["sources"]) for test in stm32["tests"])
    rp2040 = next(item for item in payload["duts"] if item["dut_id"] == "rp2040_pico")
    assert not any(test["path"] == "tests/plans/uart_banner.json" for test in rp2040["tests"])


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
    assert any(item["id"] == "esp32jtag_stm32_golden" for item in payload["probe_instances"])
    assert any(item["id"] == "esp32s3_dev_c_meter" for item in payload["instruments"])
    assert all(not item["metadata_validation_errors"] for item in payload["probe_instances"])


def test_build_instrument_instance_inventory_includes_references():
    payload = inventory.build_instrument_instance_inventory(REPO_ROOT)
    probe = next(item for item in payload["probe_instances"] if item["id"] == "esp32jtag_stm32_golden")
    meter = next(item for item in payload["instruments"] if item["id"] == "esp32s3_dev_c_meter")
    assert "stm32f103" in probe["referenced_by"]["boards"]
    assert "stm32f401rct6" in probe["referenced_by"]["boards"]
    assert "esp32c6_gpio_signature_with_meter.json" in " ".join(meter["referenced_by"]["plans"])
    assert probe["metadata_validation_errors"] == []
    assert meter["metadata_validation_errors"] == []


def test_describe_test_for_stm32f401_gpio_signature():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["probe_or_instrument"]["kind"] == "probe"
    assert payload["probe_or_instrument"]["id"] == "esp32jtag_stm32_golden"
    assert payload["probe_or_instrument"]["type"] == "esp32jtag"
    assert payload["probe_or_instrument"]["communication"]["primary"] == "gdb_remote"
    assert payload["probe_or_instrument"]["capability_surfaces"]["swd"] == "gdb_remote"
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
    assert any(check["type"] == "signal" for check in payload["expected_checks"])
    rendered = inventory.render_describe_text(payload)
    assert "connection_setup:" in rendered
    assert "source_summary:" in rendered
    assert "resolved_wiring:" in rendered
    assert "verification_views:" in rendered


def test_describe_test_warns_on_duplicate_mcu_pin_connections():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/gpio_signature.json", REPO_ROOT)
    assert len(payload["warnings"]) == 1
    assert "MCU pin PC13 is connected to 2 observation points" in payload["warnings"][0]
    assert payload["connection_setup"]["warnings"]


def test_describe_test_for_meter_path():
    payload = inventory.describe_test("esp32c6_devkit", "tests/plans/esp32c6_gpio_signature_with_meter.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["probe_or_instrument"]["kind"] == "instrument"
    assert payload["probe_or_instrument"]["id"] == "esp32s3_dev_c_meter"
    assert payload["probe_or_instrument"]["communication"]["protocol"] == "gpio_meter_v1"
    assert payload["probe_or_instrument"]["capability_surfaces"]["measure.digital"] == "primary"
    assert any(conn["from"] == "X1(GPIO4)" and conn["to"] == "inst GPIO11" for conn in payload["connections"])
    assert any(check["type"] == "instrument_measure" for check in payload["expected_checks"])
    rendered = inventory.render_describe_text(payload)
    assert "ground_required: True" in rendered
    assert "ground_confirmed: True" in rendered


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


def test_describe_test_for_stm32f401_led_blink():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/stm32f401_led_blink.json", REPO_ROOT)
    assert payload["ok"] is True
    assert any(conn["from"] == "PC13" and conn["to"] == "P0.3" for conn in payload["connections"])
    assert any(conn["from"] == "PC13" and conn["to"] == "LED" for conn in payload["connections"])
    assert any(check["type"] == "led" and check["pin"] == "led" for check in payload["expected_checks"])
    assert any(check["type"] == "signal" and check["pin"] == "led" for check in payload["expected_checks"])
