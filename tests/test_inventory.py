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
    assert "esp32c6" in payload["summary"]["mcus_with_tests"]
    assert "rp2040" in payload["summary"]["mcus_with_tests"]


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
