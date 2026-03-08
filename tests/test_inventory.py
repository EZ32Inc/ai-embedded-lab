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


def test_describe_test_for_stm32f401_gpio_signature():
    payload = inventory.describe_test("stm32f401rct6", "tests/plans/gpio_signature.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["probe_or_instrument"]["kind"] == "probe"
    assert any(conn["from"] == "SWD" and conn["to"] == "P3" for conn in payload["connections"])
    assert any(conn["from"] == "PA4" and conn["to"] == "P0.0" for conn in payload["connections"])
    assert any(check["type"] == "signal" for check in payload["expected_checks"])


def test_describe_test_for_meter_path():
    payload = inventory.describe_test("esp32c6_devkit", "tests/plans/esp32c6_gpio_signature_with_meter.json", REPO_ROOT)
    assert payload["ok"] is True
    assert payload["probe_or_instrument"]["kind"] == "instrument"
    assert payload["probe_or_instrument"]["id"] == "esp32s3_dev_c_meter"
    assert any(conn["from"] == "X1(GPIO4)" and conn["to"] == "inst GPIO11" for conn in payload["connections"])
    assert any(check["type"] == "instrument_measure" for check in payload["expected_checks"])
